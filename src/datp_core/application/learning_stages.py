"""Pipeline stages for model training, checkpoint selection, and score generation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import numpy as np
import polars as pl
from safetensors.torch import load as load_safetensors
from safetensors.torch import save as save_safetensors

from datp_core.application.stage_protocol import (
    artifact_parents,
    commit_artifact,
)
from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.domain.catalogue import ValueSweepRecord
from datp_core.domain.checkpoints import (
    select_anchor_checkpoint_round,
    select_cohort_validation_checkpoint,
    select_lowest_validation_loss_checkpoint,
)
from datp_core.domain.evaluation import MetricStatus
from datp_core.domain.identifiers import ArtifactId, DatasetId, RunId
from datp_core.domain.outcomes import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.domain.protocol_contracts import CommunicationEstimationContractRecord
from datp_core.domain.run_identity import execution_run_id
from datp_core.domain.thresholding import (
    ConformalAttainabilityStatus,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    ThresholdPolicyRecord,
)
from datp_core.domain.values import PositiveInt
from datp_core.infrastructure.learning.pytorch_adapter import (
    DittoTrainingResult,
    DynamicDenseAutoencoder,
    FederatedTrainingResult,
    derive_model_initialization_seed,
    ditto_train_autoencoder,
    federated_train_autoencoder,
    load_benign_client_tensors,
    require_cuda_training_device,
    score_materialized_split,
    score_personalized_materialized_split,
    set_deterministic_seeds,
)
from datp_core.infrastructure.tables.schemas import (
    validate_calibration_score_frame,
    validate_test_score_frame,
)
from datp_core.planning.identity import IdentityBuilder


@dataclass(frozen=True, slots=True)
class _TrainingCheckpointSelection:
    round_losses: tuple[tuple[int, float], ...]
    personalized_round_losses: tuple[tuple[int, float], ...] | None


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
            profile.kind not in {"federated_averaging_training", "federated_prox_training"}
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
        is_ditto = profile.personalization == "ditto"
        if profile.kind == "federated_prox_training":
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
                    if materialization_config.split_method == "within_client_chronological"
                    else "train"
                )
                calibration_split = (
                    "historical_calibration" if training_split == "historical_training" else "calibration"
                )
                feature_columns = (
                    features.order if features is not None else _materialized_feature_columns(materialized_path)
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


class CohortCheckpointSelectionStageHandler:
    """Freeze the sole confirmatory FedAvg checkpoint chosen from all seed calibration curves."""

    stage = StageKind.CHECKPOINT_SELECTION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        if profile.kind == "federated_prox_training":
            return self._execute_federated_proximal(job, run_id)
        if profile.personalization == "ditto":
            return self._execute_ditto(job, run_id)
        if (
            profile.checkpoint_authorization != "primary_selection_computed_once_on_natural_device_regime"
            or experiment != self._config.primary_federated_checkpoint_experiment()
            or job.context.seed is not None
            or len(job.inputs) != len(job.dependencies)
            or not job.inputs
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Checkpoint cohort selection is only valid for the configured primary FedAvg experiment",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

        selection_keys = tuple(
            ArtifactKey(
                artifact_id=ArtifactId(f"{checkpoint.artifact_id.value}:selection"),
                kind=ArtifactKind.CHECKPOINT_SELECTION,
            )
            for checkpoint in job.inputs
        )
        try:
            selections = tuple(
                self._read_training_selection(run_id, dependency, selection_key)
                for dependency, selection_key in zip(job.dependencies, selection_keys, strict=True)
            )
            checkpoint_profile = self._config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
            scheduled_rounds = tuple(int(round_number.value) for round_number in checkpoint_profile.selected_rounds)
            seed_losses = tuple(selection.round_losses for selection in selections)
            selected_round = select_cohort_validation_checkpoint(
                scheduled_rounds=scheduled_rounds,
                seed_losses=seed_losses,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = json.dumps(
            {
                "schema_version": 1,
                "selected_round": selected_round,
                "scheduled_rounds": scheduled_rounds,
                "seed_round_losses": [selection.round_losses for selection in selections],
                "selector": checkpoint_profile.selection.rule,
                "aggregation": checkpoint_profile.selection.aggregation,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, (*job.inputs, *selection_keys)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "checkpoint cohort selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _execute_federated_proximal(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        if profile.mu_grid is None or job.context.seed is not None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="FedProx coefficient selection requires its configured coefficient grid",
            )
        expected_contexts = tuple(
            StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                federated_proximal_mu=proximal_mu,
            )
            for seed in cohort.training_seeds
            for proximal_mu in profile.mu_grid
        )
        expected_dependencies = tuple(IdentityBuilder.training_job_id(context) for context in expected_contexts)
        if job.dependencies != expected_dependencies or len(job.inputs) != len(expected_contexts):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="FedProx coefficient selection does not depend on the exact configured training grid",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        try:
            primary_round, primary_key = self._primary_round()
            means = tuple(
                (
                    proximal_mu,
                    self._mean_federated_proximal_loss(
                        run_id, experiment.identifier, cohort.training_seeds, proximal_mu, primary_round
                    ),
                )
                for proximal_mu in profile.mu_grid
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        selection_keys = tuple(self._training_selection_key(context) for context in expected_contexts)
        payload = json.dumps(
            {
                "schema_version": 1,
                "selected_proximal_mu": min(means, key=lambda item: (item[1], item[0]))[0],
                "locked_primary_round": primary_round,
                "mean_benign_calibration_loss_by_mu": means,
                "selector": (
                    "lowest_natural_device_regime_benign_validation_reconstruction_error_at_the_locked_primary_round"
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, (*job.inputs, *selection_keys, primary_key)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "FedProx coefficient selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _execute_ditto(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        if (
            experiment != self._config.primary_ditto_selection_experiment()
            or profile.personalization_parameter_grid is None
            or job.context.seed is not None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Ditto weight selection is only valid for the configured natural-device grid",
            )
        contexts = tuple(
            StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                ditto_proximal_weight=weight,
            )
            for seed in cohort.training_seeds
            for weight in profile.personalization_parameter_grid
        )
        if job.dependencies != tuple(IdentityBuilder.training_job_id(context) for context in contexts):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Ditto weight selection does not depend on the exact configured training grid",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        try:
            primary_round, primary_key = self._primary_round()
            means = tuple(
                (
                    weight,
                    self._mean_ditto_personalized_loss(
                        run_id, experiment.identifier, cohort.training_seeds, weight, primary_round
                    ),
                )
                for weight in profile.personalization_parameter_grid
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        selection_keys = tuple(self._training_selection_key(context) for context in contexts)
        payload = json.dumps(
            {
                "schema_version": 1,
                "selected_ditto_proximal_weight": min(means, key=lambda item: (item[1], item[0]))[0],
                "locked_primary_round": primary_round,
                "mean_benign_calibration_loss_by_weight": means,
                "selector": (
                    "lowest_natural_device_regime_benign_validation_reconstruction_error_at_locked_global_checkpoint"
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, (*job.inputs, *selection_keys, primary_key)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "Ditto weight selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _mean_ditto_personalized_loss(
        self, run_id: RunId, experiment_id, seeds, weight: float, selected_round: int
    ) -> float:
        losses = tuple(
            self._personalized_loss_at_round(
                self._read_training_selection(
                    run_id,
                    IdentityBuilder.training_job_id(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            ditto_proximal_weight=weight,
                        )
                    ),
                    self._training_selection_key(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            ditto_proximal_weight=weight,
                        )
                    ),
                ),
                selected_round,
            )
            for seed in seeds
        )
        return sum(losses) / len(losses)

    @staticmethod
    def _personalized_loss_at_round(selection: _TrainingCheckpointSelection, selected_round: int) -> float:
        if selection.personalized_round_losses is None:
            raise ValueError("Ditto training selection evidence lacks personalized calibration losses")
        return dict(selection.personalized_round_losses)[selected_round]

    def _mean_federated_proximal_loss(
        self, run_id: RunId, experiment_id, seeds, proximal_mu: float, selected_round: int
    ) -> float:
        losses = tuple(
            dict(
                self._read_training_selection(
                    run_id,
                    IdentityBuilder.training_job_id(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            federated_proximal_mu=proximal_mu,
                        )
                    ),
                    self._training_selection_key(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            federated_proximal_mu=proximal_mu,
                        )
                    ),
                ).round_losses
            )[selected_round]
            for seed in seeds
        )
        return sum(losses) / len(losses)

    @staticmethod
    def _training_selection_key(context: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=ArtifactId(f"{IdentityBuilder.checkpoint_artifact_id(context).value}:selection"),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )

    def _read_training_selection(
        self, run_id: RunId, dependency, selection_key: ArtifactKey
    ) -> _TrainingCheckpointSelection:
        relative_path = f"runs/{run_id.value}/{dependency.value}.selection"
        if not self._repository.assess_reuse(
            relative_path,
            selection_key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError(f"Training checkpoint-selection evidence is unavailable for '{dependency.value}'")
        selection = self._repository.read(relative_path)
        if not selection.found or selection.payload_bytes is None:
            raise ValueError(f"Training checkpoint-selection evidence is unreadable for '{dependency.value}'")
        parsed = json.loads(selection.payload_bytes)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("round_losses"), list):
            raise ValueError(f"Training checkpoint-selection evidence is malformed for '{dependency.value}'")
        return _TrainingCheckpointSelection(
            round_losses=self._losses_from_payload(parsed["round_losses"], dependency),
            personalized_round_losses=(
                self._losses_from_payload(parsed["personalized_round_losses"], dependency)
                if isinstance(parsed.get("personalized_round_losses"), list)
                else None
            ),
        )

    @staticmethod
    def _losses_from_payload(items: list[object], dependency) -> tuple[tuple[int, float], ...]:
        round_losses: list[tuple[int, float]] = []
        for item in items:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], int)
                or not isinstance(item[1], (int, float))
            ):
                raise ValueError(f"Training checkpoint-selection evidence is malformed for '{dependency.value}'")
            round_losses.append((item[0], float(item[1])))
        return tuple(round_losses)

    def _primary_round(self) -> tuple[int, ArtifactKey]:
        source = self._config.primary_federated_checkpoint_experiment()
        context = StageJobContext(experiment_id=source.identifier)
        key = IdentityBuilder.cohort_checkpoint_selection_key(context)
        source_run_id = execution_run_id(source.identifier, self._config.execution_fingerprint.value)
        relative_path = (
            f"runs/{source_run_id.value}/{IdentityBuilder.cohort_checkpoint_selection_job_id(context).value}"
        )
        if not self._repository.assess_reuse(
            relative_path,
            key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError("The frozen primary FedAvg checkpoint selection is unavailable")
        selection = self._repository.read(relative_path)
        if not selection.found or selection.payload_bytes is None:
            raise ValueError("The frozen primary FedAvg checkpoint selection is unreadable")
        parsed = json.loads(selection.payload_bytes)
        selected_round = parsed.get("selected_round") if isinstance(parsed, dict) else None
        if not isinstance(selected_round, int):
            raise ValueError("The frozen primary FedAvg checkpoint selection is malformed")
        return (selected_round, key)


class ScoreGenerationStageHandler:
    """Score one authorized materialized split from its selected model checkpoint."""

    stage = StageKind.SCORE_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        split = _score_split(job.output.kind, job.context, self._config)
        if split is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Unknown score artifact kind"
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        training_path = f"runs/{run_id.value}/{IdentityBuilder.training_job_id(job.context).value}"
        selection_path, selection_key = self._selection_location(job, run_id, profile.checkpoint_authorization)
        selection = self._repository.read(selection_path)
        if not self._repository.assess_reuse(
            selection_path,
            selection_key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Selected-checkpoint evidence is unavailable or incompatible",
            )
        if not selection.found or selection.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Selected-checkpoint evidence is unreadable"
            )
        checkpoint = self._repository.read(training_path)
        personalized_key = IdentityBuilder.personalized_checkpoint_key(job.context)
        personalized_path = f"{training_path}.personalized"
        personalized = self._repository.read(personalized_path) if profile.personalization == "ditto" else None
        materialization = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.materialization_job_id(job.context).value}"
        )
        if not checkpoint.found or checkpoint.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Model checkpoint is unavailable"
            )
        if not materialization.found or materialization.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Materialization artifact is unavailable"
            )
        if profile.personalization == "ditto" and (
            not self._repository.assess_reuse(
                personalized_path,
                personalized_key,
                self._config.scientific_fingerprint,
                self._config.execution_fingerprint,
            ).can_reuse
            or personalized is None
            or not personalized.found
            or personalized.payload_bytes is None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Personalized checkpoint is unavailable or incompatible",
            )
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        features = dataset.field_schema.model_features
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            if self._config.runtime.active_execution_profile.device_policy != "cuda_required":
                raise ValueError("Score generation requires the configured CUDA-required execution profile")
            with TemporaryDirectory(prefix="datp_scoring_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization.payload_bytes)
                feature_columns = (
                    features.order if features is not None else _materialized_feature_columns(materialized_path)
                )
                selected_round = json.loads(selection.payload_bytes)["selected_round"]
                if profile.personalization == "ditto":
                    assert personalized is not None and personalized.payload_bytes is not None
                    all_states = load_safetensors(personalized.payload_bytes)
                    models = {
                        client_id: _load_checkpoint_model(
                            all_states,
                            f"round_{selected_round}.client_{client_id}.",
                            len(feature_columns),
                            tuple(int(value.value) for value in architecture.hidden_dims),
                        )
                        for client_id in pl.read_parquet(materialized_path, columns=["client_id"])["client_id"]
                        .unique()
                        .sort()
                    }
                    scores = score_personalized_materialized_split(
                        models,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                else:
                    model = _load_checkpoint_model(
                        load_safetensors(checkpoint.payload_bytes),
                        f"round_{selected_round}.",
                        len(feature_columns),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_materialized_split(
                        model,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                scores = scores.with_columns(
                    pl.lit(
                        personalized_key.artifact_id.value
                        if profile.personalization == "ditto"
                        else job.inputs[0].artifact_id.value
                    ).alias("checkpoint_artifact_id"),
                    pl.lit(job.context.seed).alias("seed"),
                    pl.lit("higher_score_means_more_anomalous").alias("score_orientation"),
                )
        except (OSError, RuntimeError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        validated = (
            validate_calibration_score_frame(scores)
            if job.output.kind
            in {
                ArtifactKind.CALIBRATION_SCORES,
                ArtifactKind.FUTURE_RECALIBRATION_SCORES,
            }
            else validate_test_score_frame(scores)
        )
        payload = BytesIO()
        validated.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(
                self._config,
                (*job.inputs, selection_key, *((personalized_key,) if profile.personalization == "ditto" else ())),
            ),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or "score artifact commit failed"
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _selection_location(self, job: StageJob, run_id: RunId, authorization: str) -> tuple[str, ArtifactKey]:
        if authorization == "primary_selection_computed_once_on_natural_device_regime":
            selection_context = StageJobContext(experiment_id=job.context.experiment_id)
            return (
                f"runs/{run_id.value}/{IdentityBuilder.cohort_checkpoint_selection_job_id(selection_context).value}",
                IdentityBuilder.cohort_checkpoint_selection_key(selection_context),
            )
        if authorization == "lookup_of_federated_averaging_primary_selection":
            source = self._config.primary_federated_checkpoint_experiment()
            selection_context = StageJobContext(experiment_id=source.identifier)
            source_run_id = execution_run_id(source.identifier, self._config.execution_fingerprint.value)
            return (
                f"runs/{source_run_id.value}/{IdentityBuilder.cohort_checkpoint_selection_job_id(selection_context).value}",
                IdentityBuilder.cohort_checkpoint_selection_key(selection_context),
            )
        selection_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.inputs[0].artifact_id.value}:selection"),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )
        return (f"runs/{run_id.value}/{IdentityBuilder.training_job_id(job.context).value}.selection", selection_key)


def _score_split(kind: ArtifactKind, context: StageJobContext, config: ResolvedProjectConfiguration) -> str | None:
    experiment = config.experiments.get(context.experiment_id)
    population = config.populations.get(context.population_id or experiment.population_ids[0])
    dataset = config.datasets.get(population.dataset_id)
    setup = dataset.setup(population.setup_id)
    materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
    temporal = materialization.split_method == "within_client_chronological"
    if kind is ArtifactKind.CALIBRATION_SCORES:
        return "historical_calibration" if temporal else "calibration"
    if kind is ArtifactKind.FUTURE_RECALIBRATION_SCORES:
        return "future_recalibration" if temporal else None
    if kind is ArtifactKind.TEST_SCORES:
        return "future_evaluation" if temporal else "test"


def _materialized_feature_columns(path: Path) -> tuple[str, ...]:
    metadata_columns = {"split", "client_id", "source_path", "source_row_index", "is_attack", "chronology_key"}
    columns = tuple(column for column in pl.read_parquet(path, n_rows=0).columns if column not in metadata_columns)
    if not columns:
        raise ValueError("Materialized dataset has no model feature columns")
    return columns


def _score_context(context: StageJobContext, *, retain_calibration_subset: bool = False) -> StageJobContext:
    return StageJobContext(
        experiment_id=context.experiment_id,
        seed=context.seed,
        partition_condition=context.partition_condition,
        population_id=context.population_id,
        federated_proximal_mu=context.federated_proximal_mu,
        ditto_proximal_weight=context.ditto_proximal_weight,
        calibration_sample_count=context.calibration_sample_count if retain_calibration_subset else None,
        calibration_replicate=context.calibration_replicate if retain_calibration_subset else None,
    )


def _calibration_sample_counts(experiment) -> tuple[int | None, ...]:
    if experiment.calibration_subset is None:
        return (None,)
    sweep_name = experiment.calibration_subset.requested_sample_count.get("from_sweep")
    values = tuple(
        int(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    )
    if not values:
        raise ValueError("Calibration subset requires a positive integer sample-count sweep")
    return values


def _mean_group_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.mean([np.std([item[index] for item in group]) for group in groups])) if groups else None


def _group_mean_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.std([np.mean([item[index] for item in group]) for group in groups])) if groups else None


def _materiality_threshold(rule: float | str) -> float:
    if isinstance(rule, float):
        return rule
    if rule == "absolute_denominator_at_least_1.0e-6":
        return 1.0e-6
    raise ValueError(f"Unsupported denominator materiality rule: {rule!r}")


def _seed_ratio_result(
    *,
    label: str,
    formula: str,
    numerator: Mapping[str, object],
    denominator: Mapping[str, object],
    materiality_rule: float | str,
    undefined_behavior: str,
) -> dict[str, object]:
    numerator_values = numerator.get("seed_differences")
    denominator_values = denominator.get("seed_differences")
    if (
        not isinstance(numerator_values, list)
        or not isinstance(denominator_values, list)
        or len(numerator_values) != len(denominator_values)
        or not all(isinstance(value, int | float) for value in (*numerator_values, *denominator_values))
    ):
        raise ValueError(f"Ratio analysis '{label}' has malformed paired seed differences")
    materiality = _materiality_threshold(materiality_rule)
    ratios = [
        None if abs(float(denominator_value)) < materiality else float(numerator_value) / float(denominator_value)
        for numerator_value, denominator_value in zip(numerator_values, denominator_values, strict=True)
    ]
    defined = [value for value in ratios if value is not None]
    return {
        "analysis_label": label,
        "formula": formula,
        "undefined_denominator_behavior": undefined_behavior,
        "per_seed_ratio": ratios,
        "defined_seed_count": len(defined),
        "mean_defined_ratio": sum(defined) / len(defined) if defined else None,
        "ratio_of_seed_means": (sum(float(value) for value in numerator_values) / len(numerator_values))
        / (sum(float(value) for value in denominator_values) / len(denominator_values))
        if abs(sum(float(value) for value in denominator_values) / len(denominator_values)) >= materiality
        else None,
    }


def _weighted_mean(values: list[tuple[int, int]]) -> float | None:
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None


def _conformal_seed_coverage(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    calibration_counts: Mapping[str, int],
    target_coverage: float,
    coverage_alpha: float,
    minimum_sample_count: int,
) -> dict[str, object]:
    required = ("finite_sample_rank", "attainability_status")
    if any(field not in thresholds.columns for field in required):
        raise ValueError("Conformal threshold artifact lacks finite-sample diagnostics")
    joined = thresholds.join(metrics, on="client_id", how="left")
    if joined.height != thresholds.height or joined["true_negatives"].null_count() > 0:
        raise ValueError("Conformal coverage metrics do not cover the threshold population")
    per_client: dict[str, dict[str, object]] = {}
    coverages: list[float] = []
    true_negatives = 0
    benign_total = 0
    for client, rank, attainability, tn, fp, fpr_status in joined.select(
        "client_id",
        "finite_sample_rank",
        "attainability_status",
        "true_negatives",
        "false_positives",
        "false_positive_rate_status",
    ).iter_rows():
        client_id = str(client)
        count = calibration_counts.get(client_id)
        if count is None or rank is None or attainability is None:
            raise ValueError("Conformal coverage inputs have incomplete per-client diagnostics")
        expected_rank = min(ceil((count + 1) * (1.0 - coverage_alpha)), count)
        expected_status = (
            ConformalAttainabilityStatus.ATTAINABLE
            if count >= max(minimum_sample_count, ceil(1.0 / coverage_alpha) - 1)
            else ConformalAttainabilityStatus.UNATTAINABLE
        )
        if int(rank) != expected_rank or attainability != expected_status.value:
            raise ValueError(f"Conformal finite-sample diagnostics disagree for client '{client_id}'")
        client_true_negatives = int(tn)
        client_benign_total = client_true_negatives + int(fp)
        if (client_benign_total > 0) != (fpr_status == MetricStatus.AVAILABLE.value):
            raise ValueError(f"Conformal coverage metric status disagrees for client '{client_id}'")
        coverage = client_true_negatives / client_benign_total if client_benign_total else None
        if coverage is not None:
            coverages.append(coverage)
            true_negatives += client_true_negatives
            benign_total += client_benign_total
        per_client[client_id] = {
            "coverage": coverage,
            "absolute_coverage_error": abs(coverage - target_coverage) if coverage is not None else None,
            "coverage_status": "available" if coverage is not None else "unavailable_no_benign_test_records",
            "finite_sample_rank": int(rank),
            "attainability_status": attainability,
            "calibration_count": count,
        }
    return {
        "per_client_coverage": per_client,
        "client_coverages": coverages,
        "finite_sample_rank": {client: values["finite_sample_rank"] for client, values in per_client.items()},
        "attainability_status": {client: values["attainability_status"] for client, values in per_client.items()},
        "benign_true_negatives": true_negatives,
        "benign_total": benign_total,
    }


def _client_score_distributions(
    thresholds: pl.DataFrame, metrics: pl.DataFrame, scores: pl.DataFrame, client_filter: str | None
) -> dict[str, object]:
    clients = {str(client) for client in thresholds["client_id"].to_list()}
    if client_filter is not None:
        if client_filter not in clients:
            raise ValueError(f"Locked client '{client_filter}' is unavailable in this evaluation")
        clients = {client_filter}
    threshold_by_client = {
        str(client): float(value) for client, value in thresholds.select("client_id", "threshold").iter_rows()
    }
    metrics_by_client = {str(row["client_id"]): row for row in metrics.to_dicts()}
    result: dict[str, object] = {}
    for client in sorted(clients):
        metric = metrics_by_client.get(client)
        if metric is None:
            raise ValueError(f"Score distribution metric is unavailable for client '{client}'")
        client_scores = scores.filter(pl.col("client_id") == client)
        threshold = threshold_by_client[client]
        benign = sorted(float(value) for value in client_scores.filter(pl.col("label") == 0)["score"].to_list())
        attack = sorted(float(value) for value in client_scores.filter(pl.col("label") == 1)["score"].to_list())
        result[client] = {
            "per_client_benign_score_cdf": _empirical_cdf(benign),
            "per_client_attack_score_cdf": _empirical_cdf(attack),
            "per_client_threshold_position": {
                "threshold": threshold,
                "benign_cdf": _cdf_position(benign, threshold),
                "attack_cdf": _cdf_position(attack, threshold),
            },
            "threshold": threshold,
            "false_positive_rate": metric["false_positive_rate"],
            "false_positive_rate_status": metric["false_positive_rate_status"],
            "true_positive_rate": metric["true_positive_rate"],
            "true_positive_rate_status": metric["true_positive_rate_status"],
            "balanced_accuracy": metric["balanced_accuracy"],
            "balanced_accuracy_status": metric["balanced_accuracy_status"],
            "macro_f1": metric["macro_f1"],
            "macro_f1_status": metric["macro_f1_status"],
        }
    return result


def _empirical_cdf(values: list[float]) -> list[dict[str, float]]:
    return [{"score": value, "cumulative_probability": (index + 1) / len(values)} for index, value in enumerate(values)]


def _cdf_position(values: list[float], threshold: float) -> float | None:
    return sum(value <= threshold for value in values) / len(values) if values else None


def _threshold_tradeoff(baseline: dict[str, object], shifted: dict[str, object]) -> dict[str, dict[str, float | None]]:
    if set(baseline) != set(shifted):
        raise ValueError("Threshold trade-off sources have incompatible client populations")
    baseline_values = cast(dict[str, dict[str, object]], baseline)
    shifted_values = cast(dict[str, dict[str, object]], shifted)
    return {
        client: {
            "threshold_shift": float(cast(float, shifted_values[client]["threshold"]))
            - float(cast(float, baseline_values[client]["threshold"])),
            "fpr_delta": _metric_delta(baseline_values[client], shifted_values[client], "false_positive_rate"),
            "tpr_delta": _metric_delta(baseline_values[client], shifted_values[client], "true_positive_rate"),
        }
        for client in sorted(baseline)
    }


def _metric_delta(baseline: object, shifted: object, metric: str) -> float | None:
    left = cast(dict[str, object], baseline).get(metric)
    right = cast(dict[str, object], shifted).get(metric)
    return float(right) - float(left) if isinstance(left, float) and isinstance(right, float) else None


def _calibration_variance_terms(calibration: pl.DataFrame) -> dict[str, float | None]:
    values = np.asarray(calibration["score"].to_list(), dtype=np.float64)
    if values.size == 0:
        raise ValueError("Quantile-estimation analysis requires calibration scores")
    pooled_variance = float(np.var(values))
    means_and_variances = []
    for _, group in calibration.group_by("client_id", maintain_order=True):
        group_values = np.asarray(group["score"].to_list(), dtype=np.float64)
        means_and_variances.append((group_values.size, float(group_values.mean()), float(np.var(group_values))))
    total = sum(count for count, _, _ in means_and_variances)
    pooled_mean = float(values.mean())
    within = sum(count * variance for count, _, variance in means_and_variances) / total
    between = sum(count * (mean - pooled_mean) ** 2 for count, mean, _ in means_and_variances) / total
    return {
        "within_term": within,
        "between_term": between,
        "between_ratio": between / pooled_variance if pooled_variance else None,
    }


def _threshold_exchange_cost(
    contract: CommunicationEstimationContractRecord, policy: ThresholdPolicyRecord, client_count: int
) -> tuple[tuple[str, ...], int]:
    if isinstance(policy, SharedMeanThresholdPolicyRecord):
        exchange = contract.threshold_exchange.b1
        candidate_count = 0
    elif isinstance(policy, LocalQuantileThresholdPolicyRecord):
        exchange = contract.threshold_exchange.b2
        candidate_count = 0
    elif isinstance(policy, FederatedMatchedExceedanceThresholdPolicyRecord):
        exchange = contract.threshold_exchange.federated_summary
        grid = policy.candidate_grid
        minimum = grid["minimum"]
        maximum = grid["maximum"]
        step = grid["step"]
        if not isinstance(minimum, float) or not isinstance(maximum, float) or not isinstance(step, float):
            raise ValueError("Federated-summary candidate grid requires finite numeric bounds")
        candidate_count = round((maximum - minimum) / step) + 1
    elif isinstance(policy, SharedPooledThresholdPolicyRecord | SharedWeightedThresholdPolicyRecord):
        return (), 0
    else:
        raise ValueError(f"No communication contract is configured for threshold policy '{policy.policy}'")
    base_fields = tuple(exchange.uplink_fields_per_client or ()) + tuple(exchange.downlink_fields_per_client or ())
    candidate_fields = tuple(exchange.candidate_grid_downlink_fields_per_client or ()) + tuple(
        exchange.candidate_grid_uplink_fields_per_client_per_candidate or ()
    )
    return (
        base_fields + candidate_fields,
        client_count
        * (
            sum(_field_bytes(contract, field) for field in base_fields)
            + candidate_count * sum(_field_bytes(contract, field) for field in candidate_fields)
        ),
    )


def _field_bytes(contract: CommunicationEstimationContractRecord, field: str) -> int:
    encoding = next((name for name in contract.field_encodings if field.endswith(name)), None)
    if encoding is None:
        raise ValueError(f"Communication field '{field}' has no configured encoding")
    return contract.field_encodings[encoding].bytes_per_field


def _ineligible_client_metrics(evaluation: pl.DataFrame) -> pl.DataFrame:
    return (
        evaluation.filter(pl.col("threshold").is_null())
        .select("client_id")
        .unique(maintain_order=True)
        .with_columns(
            pl.lit(0).alias("true_positives"),
            pl.lit(0).alias("false_positives"),
            pl.lit(0).alias("true_negatives"),
            pl.lit(0).alias("false_negatives"),
            pl.lit(None, dtype=pl.Float64).alias("false_positive_rate"),
            pl.lit("unavailable_ineligible_client").alias("false_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("true_positive_rate"),
            pl.lit("unavailable_ineligible_client").alias("true_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("balanced_accuracy"),
            pl.lit("unavailable_ineligible_client").alias("balanced_accuracy_status"),
            pl.lit(None, dtype=pl.Float64).alias("macro_f1"),
            pl.lit("unavailable_ineligible_client").alias("macro_f1_status"),
            pl.lit(None, dtype=pl.Float64).alias("auroc"),
            pl.lit("unavailable_ineligible_client").alias("auroc_status"),
        )
    )


def _load_checkpoint_model(
    states: Mapping[str, object], prefix: str, input_dimension: int, hidden_dims: tuple[int, ...]
) -> DynamicDenseAutoencoder:
    state = {name.removeprefix(prefix): tensor for name, tensor in states.items() if name.startswith(prefix)}
    if not state:
        raise ValueError("Selected checkpoint is absent from the persisted checkpoint grid")
    model = DynamicDenseAutoencoder(input_dimension, hidden_dims)
    model.load_state_dict(state)
    return model


