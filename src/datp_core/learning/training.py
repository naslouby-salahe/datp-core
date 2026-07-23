"""Pipeline stage for federated model training (FedAvg/FedProx/Ditto)."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from safetensors.torch import save as save_safetensors

from datp_core.artifacts.models import (
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.datasets.models import SplitMethod
from datp_core.experiments.identity import IdentityBuilder
from datp_core.learning.autoencoder import (
    DynamicDenseAutoencoder,
    derive_model_initialization_seed,
    require_cuda_training_device,
    set_deterministic_seeds,
)
from datp_core.learning.checkpoints import select_anchor_checkpoint_round, select_lowest_validation_loss_checkpoint
from datp_core.learning.federated import FederatedTrainingResult, federated_train_autoencoder
from datp_core.learning.models import PersonalizationStrategy, TrainingProfileKind
from datp_core.learning.personalization import DittoTrainingResult, ditto_train_autoencoder
from datp_core.learning.scoring import load_benign_client_tensors, materialized_feature_columns
from datp_core.pipeline.identifiers import DatasetId, RunId
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact
from datp_core.pipeline.values import PositiveInt


class ModelTrainingStageHandler:
    """Train one configured full-participation federated model and persist its checkpoint grid."""

    stage = StageKind.MODEL_TRAINING

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        if (
            profile.kind
            not in {TrainingProfileKind.FEDERATED_AVERAGING_TRAINING, TrainingProfileKind.FEDERATED_PROX_TRAINING}
            or profile.participation != "full"
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=f"Training profile '{profile.identifier.value}' is not implemented by the FedAvg stage",
            )
        if job.context.seed is None or profile.local_epochs is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Training requires a seed and local epochs"
            )
        proximal_mu = job.context.federated_proximal_mu
        ditto_weight = job.context.ditto_proximal_weight
        is_ditto = profile.personalization == PersonalizationStrategy.DITTO
        if profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
            if proximal_mu is None or proximal_mu <= 0.0 or ditto_weight is not None:
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message="FedProx training requires a positive sweep-resolved mu",
                )
        elif is_ditto:
            if (
                proximal_mu is not None
                or ditto_weight is None
                or ditto_weight <= 0.0
                or profile.personalized_local_epochs is None
            ):
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message="Ditto training requires a positive sweep-resolved personalization weight",
                )
        elif proximal_mu is not None or ditto_weight is not None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="FedAvg training must not carry a FedProx coefficient"
            )
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        setup = dataset.setup(population.setup_id)
        materialization_config = next(
            item for item in dataset.materializations if item.identifier == setup.materialization_id
        )
        features = dataset.field_schema.model_features
        checkpoint_profile = self._config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
        if checkpoint_profile.total_rounds is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Checkpoint profile has no round budget"
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        selection_relative_path = f"{relative_path}.selection"
        personalized_relative_path = f"{relative_path}.personalized"
        personalized_key = IdentityBuilder.personalized_checkpoint_key(job.context)
        selection_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.output.artifact_id.value}:selection"), kind=ArtifactKind.CHECKPOINT_SELECTION
        )
        reuse = self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        )
        if (
            reuse.can_reuse
            and self._repository.assess_reuse(
                selection_relative_path,
                selection_key,
                self._config.scientific_fingerprint,
                self._config.execution_fingerprint,
            ).can_reuse
            and (
                not is_ditto
                or self._repository.assess_reuse(
                    personalized_relative_path,
                    personalized_key,
                    self._config.scientific_fingerprint,
                    self._config.execution_fingerprint,
                ).can_reuse
            )
        ):
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        materialization_path = f"runs/{run_id.value}/{IdentityBuilder.materialization_job_id(job.context).value}"
        materialization = self._repository.read(materialization_path)
        if not materialization.found or materialization.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Materialization artifact is unavailable"
            )
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        optimizer = self._config.optimizers.get(profile.optimizer_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            with TemporaryDirectory(prefix="datp_training_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization.payload_bytes)
                training_split = (
                    "historical_training"
                    if materialization_config.split_method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL
                    else "train"
                )
                calibration_split = (
                    "historical_calibration" if training_split == "historical_training" else "calibration"
                )
                feature_columns = (
                    features.order if features is not None else materialized_feature_columns(materialized_path)
                )
                training_clients = load_benign_client_tensors(materialized_path, training_split, feature_columns)
                calibration_clients = load_benign_client_tensors(materialized_path, calibration_split, feature_columns)
                if self._config.runtime.active_execution_profile.device_policy != "cuda_required":
                    raise ValueError("Model training requires the configured CUDA-required execution profile")
                initialization_namespace = self._config.protocol_determinism.seed_namespaces["model_initialization"]
                shuffle_namespace = self._config.protocol_determinism.seed_namespaces["dataloader_shuffle"]
                digest_bytes = int(self._config.protocol_determinism.derived_seed_algorithm["digest_bytes"])
                initialization_seed = derive_model_initialization_seed(
                    key=initialization_namespace.key,
                    digest_bytes=digest_bytes,
                    training_seed=job.context.seed,
                )
                set_deterministic_seeds(initialization_seed)
                model = DynamicDenseAutoencoder(
                    len(feature_columns), tuple(int(value.value) for value in architecture.hidden_dims)
                )
                training_kwargs = {
                    "rounds": int(checkpoint_profile.total_rounds.value),
                    "local_epochs": int(profile.local_epochs.value),
                    "learning_rate": float(optimizer.learning_rate.value),
                    "batch_size": int(batching.micro_batch_size.value),
                    "seed": job.context.seed,
                    "device": require_cuda_training_device(),
                    "beta_1": optimizer.beta_1,
                    "beta_2": optimizer.beta_2,
                    "epsilon": float(optimizer.epsilon.value),
                    "weight_decay": float(optimizer.weight_decay.value),
                    "amsgrad": optimizer.amsgrad,
                    "shuffle_each_epoch": batching.shuffle_each_epoch,
                    "checkpoint_rounds": tuple(int(value.value) for value in checkpoint_profile.selected_rounds),
                    "shuffle_seed_key": shuffle_namespace.key,
                    "shuffle_seed_digest_bytes": digest_bytes,
                }
                result = (
                    ditto_train_autoencoder(
                        model,
                        training_clients,
                        calibration_clients,
                        personalized_local_epochs=int(cast(PositiveInt, profile.personalized_local_epochs).value),
                        proximal_weight=cast(float, ditto_weight),
                        **training_kwargs,
                    )
                    if is_ditto
                    else federated_train_autoencoder(
                        model, training_clients, calibration_clients, proximal_mu=proximal_mu, **training_kwargs
                    )
                )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        if is_ditto:
            ditto_result = cast(DittoTrainingResult, result)
            round_losses = ditto_result.global_round_losses
            personalized_round_losses = ditto_result.personalized_round_losses
            scheduled_rounds = tuple(checkpoint.round_number for checkpoint in ditto_result.scheduled_checkpoints)
            derived_shuffle_seeds = ditto_result.derived_shuffle_seeds
            checkpoint_grid = {
                f"round_{checkpoint.round_number}.{name}": tensor
                for checkpoint in ditto_result.scheduled_checkpoints
                for name, tensor in checkpoint.global_state
            }
        else:
            federated_result = cast(FederatedTrainingResult, result)
            round_losses = federated_result.round_losses
            personalized_round_losses = None
            scheduled_rounds = tuple(checkpoint.round_number for checkpoint in federated_result.scheduled_checkpoints)
            derived_shuffle_seeds = federated_result.derived_shuffle_seeds
            checkpoint_grid = {
                f"round_{checkpoint.round_number}.{name}": tensor
                for checkpoint in federated_result.scheduled_checkpoints
                for name, tensor in checkpoint.state
            }
        if checkpoint_profile.convergence is not None:
            selected_round = select_anchor_checkpoint_round(
                convergence=checkpoint_profile.convergence,
                recorded_losses=round_losses,
                round_cap=int(checkpoint_profile.total_rounds.value),
            )
        else:
            selected_round = select_lowest_validation_loss_checkpoint(
                scheduled_rounds=tuple(int(value.value) for value in checkpoint_profile.selected_rounds),
                recorded_losses=round_losses,
            )
        if selected_round not in scheduled_rounds:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Selected checkpoint state was not captured"
            )
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.SAFETENSORS,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=save_safetensors(checkpoint_grid)),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or "checkpoint commit failed"
            )
        if is_ditto:
            ditto_result = cast(DittoTrainingResult, result)
            personalized_grid = {
                f"round_{checkpoint.round_number}.client_{client_id}.{name}": tensor
                for checkpoint in ditto_result.scheduled_checkpoints
                for client_id, state in checkpoint.personalized_states
                for name, tensor in state
            }
            personalized_commit = commit_artifact(
                self._repository,
                self._config,
                job.context,
                artifact_key=personalized_key,
                artifact_format=ArtifactFormat.SAFETENSORS,
                relative_path=personalized_relative_path,
                parents=artifact_parents(self._config, job.inputs),
                payload=BytesPayload(payload_bytes=save_safetensors(personalized_grid)),
            )
            if not personalized_commit.success:
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message=personalized_commit.error_message or "personalized checkpoint commit failed",
                )
        selection_payload = json.dumps(
            {
                "schema_version": 1,
                "selected_round": selected_round,
                "checkpoint_rounds": scheduled_rounds,
                "round_losses": round_losses,
                "personalized_round_losses": personalized_round_losses,
                "ditto_proximal_weight": ditto_weight,
                "model_initialization_seed": initialization_seed,
                "dataloader_shuffle_seeds": [
                    [seed.round_number, seed.client_id, seed.local_epoch, seed.value] for seed in derived_shuffle_seeds
                ],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        selection_commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=selection_key,
            artifact_format=ArtifactFormat.JSON,
            relative_path=selection_relative_path,
            parents=artifact_parents(self._config, (job.output,)),
            payload=BytesPayload(payload_bytes=selection_payload),
        )
        if not selection_commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=selection_commit.error_message or "selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
