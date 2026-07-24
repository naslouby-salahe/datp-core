"""Pipeline stage for federated model training (FedAvg/FedProx/Ditto)."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from safetensors.torch import save as save_safetensors

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind, ArtifactReuseReason
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.models import ArtifactReuseDecision
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.hashing import compute_payload_checksum
from datp_core.core.identifiers import ArtifactId, DatasetId, RunId
from datp_core.core.numbers import PositiveInt
from datp_core.data.contracts import SplitMethod
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.identity.kinds import IdentityKind
from datp_core.learning.checkpoints.selection import (
    select_anchor_checkpoint_round,
    select_lowest_validation_loss_checkpoint,
)
from datp_core.learning.contracts.enums import (
    DevicePolicy,
    PersonalizationStrategy,
    TrainingParticipation,
    TrainingProfileKind,
)
from datp_core.learning.model.autoencoder import DynamicDenseAutoencoder
from datp_core.learning.model.determinism import derive_model_initialization_seed, set_deterministic_seeds
from datp_core.learning.model.device import require_cuda_training_device
from datp_core.learning.scoring.data import load_benign_client_tensors, materialized_feature_columns
from datp_core.learning.training.federated import federated_train_autoencoder
from datp_core.learning.training.models import DittoTrainingResult, FederatedTrainingResult
from datp_core.learning.training.personalization import ditto_train_autoencoder
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class ModelTrainingStageHandler:
    """Train one configured full-participation federated model and persist its checkpoint grid."""

    stage = StageKind.MODEL_TRAINING

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def _verify_or_commit(
        self,
        job: StageJob,
        *,
        reuse: ArtifactReuseDecision,
        payload_bytes: bytes,
        artifact_key: ArtifactKey,
        artifact_format: ArtifactFormat,
        relative_path: str,
        parents: tuple[object, ...],
        label: str,
    ) -> StageJobOutcome | None:
        """Complete one member of the training family: verify a matching partial member (already
        frozen) reproduces byte-identically before skipping it, or commit a genuinely missing one.
        Training is deterministic given a fixed seed (`set_deterministic_seeds`, CUDA-required
        execution profile), so recomputing to complete a partial family is scientifically valid --
        expensive, but not a fabricated shortcut. Returns a failure outcome, or ``None`` to continue."""
        if reuse.can_reuse:
            recomputed_checksum = compute_payload_checksum(payload_bytes)
            existing_checksum = reuse.existing_manifest.payload_checksum if reuse.existing_manifest else None
            if existing_checksum is None or recomputed_checksum != existing_checksum:
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message=(
                        f"Recomputed {label} conflicts with the already-frozen artifact: expected "
                        f"payload checksum {existing_checksum}, recomputed {recomputed_checksum}."
                    ),
                )
            return None
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=artifact_key,
            artifact_format=artifact_format,
            relative_path=relative_path,
            parents=parents,  # type: ignore[arg-type]
            payload=BytesPayload(payload_bytes=payload_bytes),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or f"{label} commit failed"
            )
        return None

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        if (
            profile.kind
            not in {TrainingProfileKind.FEDERATED_AVERAGING_TRAINING, TrainingProfileKind.FEDERATED_PROX_TRAINING}
            or profile.participation != TrainingParticipation.FULL.value
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
        personalized_key = IdentityBuilder.artifact_key(IdentityKind.PERSONALIZED_CHECKPOINT, job.context)
        selection_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.output.artifact_id.value}:selection"), kind=ArtifactKind.CHECKPOINT_SELECTION
        )
        reuse = self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        )
        selection_reuse = self._repository.assess_reuse(
            selection_relative_path,
            selection_key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        )
        personalized_reuse: ArtifactReuseDecision | None = (
            self._repository.assess_reuse(
                personalized_relative_path,
                personalized_key,
                self._config.scientific_fingerprint,
                self._config.execution_fingerprint,
            )
            if is_ditto
            else None
        )
        personalized_complete = personalized_reuse is None or personalized_reuse.can_reuse
        if reuse.can_reuse and selection_reuse.can_reuse and personalized_complete:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        # A companion that exists but disagrees (wrong key/format/fingerprint) is a conflicting
        # partial family -- fail explicitly before retraining, never overwrite it.
        for label, decision in (("selection", selection_reuse), ("personalized checkpoint", personalized_reuse)):
            if (
                decision is not None
                and not decision.can_reuse
                and ArtifactReuseReason.ARTIFACT_NOT_COMMITTED not in decision.reason
            ):
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message=(
                        f"Training {label} companion conflicts with a previously committed artifact: "
                        f"{[reason.value for reason in decision.reason]}"
                    ),
                )
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
                if self._config.runtime.active_execution_profile.device_policy != DevicePolicy.CUDA_REQUIRED.value:
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
        checkpoint_outcome = self._verify_or_commit(
            job,
            reuse=reuse,
            payload_bytes=save_safetensors(checkpoint_grid),
            artifact_key=job.output,
            artifact_format=ArtifactFormat.SAFETENSORS,
            relative_path=relative_path,
            parents=artifact_parents(self._config, ((job.inputs[0], materialization_path),)),
            label="training checkpoint",
        )
        if checkpoint_outcome is not None:
            return checkpoint_outcome
        if is_ditto:
            ditto_result = cast(DittoTrainingResult, result)
            personalized_grid = {
                f"round_{checkpoint.round_number}.client_{client_id}.{name}": tensor
                for checkpoint in ditto_result.scheduled_checkpoints
                for client_id, state in checkpoint.personalized_states
                for name, tensor in state
            }
            assert personalized_reuse is not None  # guarded by is_ditto above
            personalized_outcome = self._verify_or_commit(
                job,
                reuse=personalized_reuse,
                payload_bytes=save_safetensors(personalized_grid),
                artifact_key=personalized_key,
                artifact_format=ArtifactFormat.SAFETENSORS,
                relative_path=personalized_relative_path,
                parents=artifact_parents(self._config, ((job.inputs[0], materialization_path),)),
                label="personalized checkpoint",
            )
            if personalized_outcome is not None:
                return personalized_outcome
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
            allow_nan=False,
        ).encode("utf-8")
        selection_outcome = self._verify_or_commit(
            job,
            reuse=selection_reuse,
            payload_bytes=selection_payload,
            artifact_key=selection_key,
            artifact_format=ArtifactFormat.JSON,
            relative_path=selection_relative_path,
            parents=artifact_parents(self._config, ((job.output, relative_path),)),
            label="selection evidence",
        )
        if selection_outcome is not None:
            return selection_outcome
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
