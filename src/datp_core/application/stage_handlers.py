"""Application-facing stage-handler contracts and real preflight execution."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from typing import Protocol, cast

import polars as pl
from safetensors.torch import load as load_safetensors
from safetensors.torch import save as save_safetensors

from datp_core.application.dataset_audit import AuditDatasetUseCase
from datp_core.application.reporting import ResultFreezeError, freeze_result_family, render_frozen_report
from datp_core.application.statistical_analysis import StatisticalAnalysisUseCase
from datp_core.application.threshold_construction import ConstructThresholdsUseCase
from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactParent,
    ArtifactRepository,
    BytesPayload,
    FilePayload,
)
from datp_core.domain.catalogue import (
    ConditionSweepRecord,
    MetricAssociationAnalysisRecord,
    PairedThresholdAnalysisRecord,
    SweepConditionRecord,
    ThresholdStabilityAnalysisRecord,
    ValueSweepRecord,
)
from datp_core.domain.checkpoints import (
    select_anchor_checkpoint_round,
    select_cohort_validation_checkpoint,
    select_lowest_validation_loss_checkpoint,
)
from datp_core.domain.datasets import PartitionSeedContract
from datp_core.domain.evaluation import MetricStatus, calculate_fpr_dispersion, calculate_pairwise_js_divergence
from datp_core.domain.identifiers import ArtifactId, ClientId, DatasetId, RunId
from datp_core.domain.outcomes import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.domain.run_identity import execution_run_id
from datp_core.domain.thresholding import BenignCalibrationScores
from datp_core.domain.values import PositiveInt, Seed
from datp_core.infrastructure.datasets.adapter_registry import DatasetAdapterRegistry
from datp_core.infrastructure.datasets.source_inventory import build_source_inventory
from datp_core.infrastructure.datasets.split_manifest import encode_split_manifest, read_materialized_split_evidence
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
from datp_core.infrastructure.tables.calibration_subsampling import subsample_calibration_scores
from datp_core.infrastructure.tables.polars_engine import compute_operating_point_metrics
from datp_core.infrastructure.tables.schemas import (
    validate_calibration_score_frame,
    validate_client_metric_frame,
    validate_test_score_frame,
    validate_threshold_frame,
)
from datp_core.planning.identity import IdentityBuilder


class StageHandler(Protocol):
    """One executable stage that may only report success after an artifact commit."""

    stage: StageKind

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome: ...


@dataclass(frozen=True, slots=True)
class _TrainingCheckpointSelection:
    round_losses: tuple[tuple[int, float], ...]
    personalized_round_losses: tuple[tuple[int, float], ...] | None


def _commit_artifact(
    repository: ArtifactRepository,
    config: ResolvedProjectConfiguration,
    context: StageJobContext,
    *,
    artifact_key: ArtifactKey,
    artifact_format: ArtifactFormat,
    relative_path: str,
    parents: tuple[ArtifactParent, ...],
    payload: BytesPayload | FilePayload,
):
    return repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=artifact_format,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=parents,
                schema_version=1,
                creation_timestamp=time(),
                environment_identity=config.runtime.bootstrap.environment_identity,
                experiment_id=context.experiment_id,
                seed=Seed(context.seed) if context.seed is not None else None,
            ),
            payload=payload,
        )
    )


def _parents(config: ResolvedProjectConfiguration, artifacts: tuple[ArtifactKey, ...]) -> tuple[ArtifactParent, ...]:
    return tuple(
        ArtifactParent(parent_key=artifact, scientific_fingerprint=config.scientific_fingerprint)
        for artifact in artifacts
    )


def _partition_contract(
    config: ResolvedProjectConfiguration, experiment_id, condition_name: str | None
) -> tuple[SweepConditionRecord | None, PartitionSeedContract | None]:
    if condition_name is None:
        return (None, None)
    experiment = config.experiments.get(experiment_id)
    matches = tuple(
        condition
        for sweep in experiment.sweeps
        if isinstance(sweep, ConditionSweepRecord)
        for condition in sweep.conditions
        if condition.name == condition_name
    )
    if len(matches) != 1:
        raise ValueError(f"Experiment '{experiment_id.value}' has no unique partition condition '{condition_name}'")
    try:
        namespace = config.protocol_determinism.seed_namespaces["partition"]
        digest_bytes = PositiveInt(int(config.protocol_determinism.derived_seed_algorithm["digest_bytes"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Protocol determinism lacks a valid partition seed namespace") from exc
    return (matches[0], PartitionSeedContract(key=namespace.key, digest_bytes=digest_bytes))


class PreflightStageHandler:
    """Commit resolved configuration identity after source-readiness validation."""

    stage = StageKind.PREFLIGHT

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        payload = json.dumps(
            {
                "run_id": run_id.value,
                "schema_version": 1,
                "scientific_fingerprint": self._config.scientific_fingerprint.value,
                "execution_fingerprint": self._config.execution_fingerprint.value,
                "scientific_projection": self._config.scientific_projection,
                "execution_projection": self._config.execution_projection,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        reuse = self._repository.assess_reuse(
            relative_path,
            job.output,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        )
        if reuse.can_reuse:
            return StageJobOutcome.reused(
                job_id=job.job_id,
                stage=job.stage,
                produced_artifact=job.output,
            )
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=(),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "artifact commit failed",
            )
        return StageJobOutcome.succeeded(
            job_id=job.job_id,
            stage=job.stage,
            produced_artifact=job.output,
        )


class DatasetMaterializationStageHandler:
    """Materialize one dataset through its registered adapter and commit the resulting Parquet artifact.

    No dataset-specific imports or raw ID parsing. The handler resolves the
    experiment/population/dataset/setup, assesses reuse, selects the adapter
    by AdapterKind, builds the source inventory, requests materialization,
    and commits the staged artifact.
    """

    stage = StageKind.DATASET_MATERIALIZATION

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        repository: ArtifactRepository,
        adapter_registry: DatasetAdapterRegistry,
    ) -> None:
        self._config = config
        self._repository = repository
        self._adapter_registry = adapter_registry

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment_id = job.context.experiment_id
        experiment = self._config.experiments.get(experiment_id)
        population = self._config.populations.get(experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]

        setup = dataset.setup(population.setup_id)
        materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)

        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        manifest_relative_path = f"{relative_path}.split_manifest"
        readiness_relative_path = f"{relative_path}.readiness"
        preprocessing_relative_path = f"{relative_path}.preprocessing"
        partition_relative_path = f"{relative_path}.partition_manifest"
        manifest_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.output.artifact_id.value}:split_manifest"),
            kind=ArtifactKind.SPLIT_MANIFEST,
        )
        readiness_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.output.artifact_id.value}:readiness"),
            kind=ArtifactKind.DATASET_READINESS,
        )
        preprocessing_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.output.artifact_id.value}:preprocessing"),
            kind=ArtifactKind.PREPROCESSING_EVIDENCE,
        )
        partition_key = (
            ArtifactKey(
                artifact_id=ArtifactId(f"{job.output.artifact_id.value}:partition_manifest"),
                kind=ArtifactKind.PARTITION_MANIFEST,
            )
            if setup.client_construction.method == "dirichlet_partitioned_clients"
            else None
        )
        try:
            partition_condition, partition_seed_contract = _partition_contract(
                self._config, experiment_id, job.context.partition_condition
            )
        except ValueError as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        if (partition_key is None) != (partition_condition is None):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Dataset setup and job partition condition are incompatible",
            )
        reuse = self._repository.assess_reuse(
            relative_path,
            job.output,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        )
        if reuse.can_reuse:
            companion_artifacts = (
                (manifest_relative_path, manifest_key),
                (readiness_relative_path, readiness_key),
                (preprocessing_relative_path, preprocessing_key),
            )
            if partition_key is not None:
                companion_artifacts += ((partition_relative_path, partition_key),)
            companion_reusable = all(
                self._repository.assess_reuse(
                    companion_path,
                    companion_key,
                    self._config.scientific_fingerprint,
                    self._config.execution_fingerprint,
                ).can_reuse
                for companion_path, companion_key in companion_artifacts
            )
            if not companion_reusable:
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message="Materialized artifact lacks compatible immutable split and readiness evidence",
                )
            return StageJobOutcome.reused(
                job_id=job.job_id,
                stage=job.stage,
                produced_artifact=job.output,
            )

        try:
            adapter = self._adapter_registry.get(dataset.adapter_kind)
        except KeyError as exc:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=str(exc),
            )

        inventory = build_source_inventory(dataset)

        try:
            with TemporaryDirectory(prefix=f"datp_{dataset.dataset_id.value}_") as staging_directory:
                staging_root = Path(staging_directory)
                payload = adapter.materialize(
                    dataset=dataset,
                    setup=setup,
                    materialization=materialization,
                    inventory=inventory,
                    staging_root=staging_root,
                    partition_condition=partition_condition,
                    partition_seed_contract=partition_seed_contract,
                )
                eligibility = self._config.eligibility_policies.get(dataset.eligibility_policy_id)
                split_evidence = read_materialized_split_evidence(
                    str(payload.staged_path), int(eligibility.minimum_benign_calibration_count)
                )
                readiness = AuditDatasetUseCase().assess_materialization(
                    dataset, setup, split_evidence, inventory.fingerprint()
                )
                if not readiness.ready_for_training:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message="Dataset readiness failed: "
                        + "; ".join(defect.code for defect in readiness.blocking_defects),
                    )
                split_manifest_payload = encode_split_manifest(split_evidence.manifest)
                commit = _commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=job.output,
                    artifact_format=ArtifactFormat.PARQUET,
                    relative_path=relative_path,
                    parents=_parents(self._config, job.inputs),
                    payload=FilePayload(source_file=str(payload.staged_path)),
                )
                if not commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=commit.error_message or "materialized artifact commit failed",
                    )
                manifest_commit = _commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=manifest_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=manifest_relative_path,
                    parents=_parents(self._config, (job.output,)),
                    payload=BytesPayload(payload_bytes=split_manifest_payload),
                )
                if not manifest_commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=manifest_commit.error_message or "split manifest commit failed",
                    )
                readiness_commit = _commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=readiness_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=readiness_relative_path,
                    parents=_parents(self._config, (job.output,)),
                    payload=BytesPayload(payload_bytes=readiness.encode()),
                )
                if not readiness_commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=readiness_commit.error_message or "dataset readiness commit failed",
                    )
                preprocessing_commit = _commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=preprocessing_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=preprocessing_relative_path,
                    parents=_parents(self._config, (job.output,)),
                    payload=BytesPayload(payload_bytes=payload.preprocessing_evidence),
                )
                if not preprocessing_commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=preprocessing_commit.error_message or "preprocessing evidence commit failed",
                    )
                if partition_key is not None:
                    if payload.partition_evidence is None:
                        return StageJobOutcome.failed(
                            job_id=job.job_id,
                            stage=job.stage,
                            error_message="Dirichlet materialization did not produce partition evidence",
                        )
                    partition_commit = _commit_artifact(
                        self._repository,
                        self._config,
                        job.context,
                        artifact_key=partition_key,
                        artifact_format=ArtifactFormat.JSON,
                        relative_path=partition_relative_path,
                        parents=_parents(self._config, (job.output,)),
                        payload=BytesPayload(payload_bytes=payload.partition_evidence),
                    )
                    if not partition_commit.success:
                        return StageJobOutcome.failed(
                            job_id=job.job_id,
                            stage=job.stage,
                            error_message=partition_commit.error_message or "partition manifest commit failed",
                        )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


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
        population = self._config.populations.get(experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        features = dataset.field_schema.model_features
        if features is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Dataset has no model feature schema"
            )
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
                training_clients = load_benign_client_tensors(materialized_path, "train", features.order)
                calibration_clients = load_benign_client_tensors(materialized_path, "calibration", features.order)
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
                    len(features.order), tuple(int(value.value) for value in architecture.hidden_dims)
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
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.SAFETENSORS,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
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
            personalized_commit = _commit_artifact(
                self._repository,
                self._config,
                job.context,
                artifact_key=personalized_key,
                artifact_format=ArtifactFormat.SAFETENSORS,
                relative_path=personalized_relative_path,
                parents=_parents(self._config, job.inputs),
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
        selection_commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=selection_key,
            artifact_format=ArtifactFormat.JSON,
            relative_path=selection_relative_path,
            parents=_parents(self._config, (job.output,)),
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
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=_parents(self._config, (*job.inputs, *selection_keys)),
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
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=_parents(self._config, (*job.inputs, *selection_keys, primary_key)),
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
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=_parents(self._config, (*job.inputs, *selection_keys, primary_key)),
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
        split = _score_split(job.output.kind)
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
        population = self._config.populations.get(experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        features = dataset.field_schema.model_features
        if features is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Dataset has no model feature schema"
            )
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            if self._config.runtime.active_execution_profile.device_policy != "cuda_required":
                raise ValueError("Score generation requires the configured CUDA-required execution profile")
            with TemporaryDirectory(prefix="datp_scoring_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization.payload_bytes)
                selected_round = json.loads(selection.payload_bytes)["selected_round"]
                if profile.personalization == "ditto":
                    assert personalized is not None and personalized.payload_bytes is not None
                    all_states = load_safetensors(personalized.payload_bytes)
                    models = {
                        client_id: _load_checkpoint_model(
                            all_states,
                            f"round_{selected_round}.client_{client_id}.",
                            len(features.order),
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
                        feature_columns=features.order,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                else:
                    model = _load_checkpoint_model(
                        load_safetensors(checkpoint.payload_bytes),
                        f"round_{selected_round}.",
                        len(features.order),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_materialized_split(
                        model,
                        materialized_path,
                        split=split,
                        feature_columns=features.order,
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
            validate_calibration_score_frame(scores) if split == "calibration" else validate_test_score_frame(scores)
        )
        payload = BytesIO()
        validated.write_parquet(payload)
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=_parents(
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


def _score_split(kind: ArtifactKind) -> str | None:
    if kind is ArtifactKind.CALIBRATION_SCORES:
        return "calibration"
    if kind is ArtifactKind.TEST_SCORES:
        return "test"


def _score_context(context: StageJobContext, *, retain_calibration_subset: bool = False) -> StageJobContext:
    return StageJobContext(
        experiment_id=context.experiment_id,
        seed=context.seed,
        partition_condition=context.partition_condition,
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


class CalibrationSubsamplingStageHandler:
    """Persist one nested, benign-only calibration window without retraining or rescoring."""

    stage = StageKind.CALIBRATION_SUBSAMPLING

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        context = job.context
        if context.seed is None or context.calibration_sample_count is None or context.calibration_replicate is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subsampling requires a seed, sample count, and replicate",
            )
        experiment = self._config.experiments.get(context.experiment_id)
        subset = experiment.calibration_subset
        if subset is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subsampling is not configured for this experiment",
            )
        if (
            subset.selection_strategy != "deterministic_without_replacement"
            or subset.nesting_policy != "nested_by_size"
            or subset.model_retraining != "never_thresholds_only_recomputed"
            or subset.replicate_seed_derivation != "derived_seed_algorithm_with_namespace_calibration_subsample"
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subset contract is not executable by the configured deterministic sampler",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        calibration = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(_score_context(context)).value}"
        )
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        try:
            namespace = self._config.protocol_determinism.seed_namespaces["calibration_subsample"]
            digest_bytes = int(self._config.protocol_determinism.derived_seed_algorithm["digest_bytes"])
            scores = validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes)))
            sampled = subsample_calibration_scores(
                scores,
                requested_sample_count=context.calibration_sample_count,
                training_seed=context.seed,
                selection_seed=subset.selection_seed.value,
                replicate=context.calibration_replicate,
                namespace_key=namespace.key,
                digest_bytes=digest_bytes,
            )
            validate_calibration_score_frame(sampled)
        except (KeyError, OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        sampled.write_parquet(payload)
        commit = _commit_artifact(
            self._repository,
            self._config,
            context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "calibration subset commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class ThresholdConstructionStageHandler:
    """Construct one configured threshold set from immutable benign calibration scores."""

    stage = StageKind.THRESHOLD_CONSTRUCTION

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        repository: ArtifactRepository,
        thresholds: ConstructThresholdsUseCase,
    ) -> None:
        self._config = config
        self._repository = repository
        self._thresholds = thresholds

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        if job.context.threshold_policy_id is None or job.context.population_id is None or job.context.seed is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Threshold construction requires policy, population, and seed",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        calibration_context = _score_context(
            job.context, retain_calibration_subset=job.context.calibration_sample_count is not None
        )
        calibration_job_id = (
            IdentityBuilder.calibration_subset_job_id(calibration_context)
            if calibration_context.calibration_sample_count is not None
            else IdentityBuilder.calibration_score_job_id(calibration_context)
        )
        calibration = self._repository.read(f"runs/{run_id.value}/{calibration_job_id.value}")
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        experiment = self._config.experiments.get(job.context.experiment_id)
        population = self._config.populations.get(job.context.population_id)
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        evaluation = next((item for item in experiment.evaluations if item.label == job.context.evaluation_label), None)
        if evaluation is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Evaluation configuration is unavailable"
            )
        if (
            evaluation.overrides
            and job.context.threshold_quantile is None
            and job.context.shrinkage_weight is None
            and job.context.federated_summary_fixed_k is None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Sweep-derived threshold overrides require explicit expanded jobs",
            )
        try:
            scores = pl.read_parquet(BytesIO(calibration.payload_bytes))
            validate_calibration_score_frame(scores)
            if scores.is_empty():
                output = pl.DataFrame(
                    schema={
                        "client_id": pl.String,
                        "threshold": pl.Float64,
                        "owner_kind": pl.String,
                        "effective_lambda": pl.Float64,
                        "policy_id": pl.String,
                        "target_quantile": pl.Float64,
                    }
                )
            else:
                grouped = tuple(
                    BenignCalibrationScores(
                        client_id=ClientId(str(client_id[0])),
                        values=tuple(float(value) for value in rows["score"].to_list()),
                        population_id=job.context.population_id,
                    )
                    for client_id, rows in scores.group_by("client_id", maintain_order=True)
                )
                threshold_set = self._thresholds.execute(
                    job.context.threshold_policy_id,
                    grouped,
                    job.context.population_id,
                    dict(dataset.field_schema.label_fields.family_map)
                    if dataset.field_schema.label_fields.family_map
                    else None,
                    Seed(job.context.seed),
                    (
                        job.context.shrinkage_weight
                        if job.context.shrinkage_weight is not None
                        else job.context.federated_summary_fixed_k
                    ),
                    job.context.threshold_quantile,
                )
                output = pl.DataFrame(
                    {
                        "client_id": [record.client_id.value for record in threshold_set.values],
                        "threshold": [float(record.threshold) for record in threshold_set.values],
                        "owner_kind": [record.owner for record in threshold_set.values],
                        "effective_lambda": [record.effective_lambda for record in threshold_set.values],
                        "policy_id": [threshold_set.policy_id.value] * len(threshold_set.values),
                        "target_quantile": [threshold_set.target_quantile.value] * len(threshold_set.values),
                    }
                )
            validate_threshold_frame(output)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        output.write_parquet(payload)
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "threshold artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class OperatingPointEvaluationStageHandler:
    """Evaluate configured thresholds against immutable test scores without score reuse across roles."""

    stage = StageKind.OPERATING_POINT_EVALUATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        thresholds = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(job.context).value}")
        scores = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(_score_context(job.context)).value}"
        )
        if not thresholds.found or thresholds.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Threshold artifact is unavailable"
            )
        if not scores.found or scores.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Test score artifact is unavailable"
            )
        try:
            threshold_frame = validate_threshold_frame(pl.read_parquet(BytesIO(thresholds.payload_bytes)))
            score_frame = validate_test_score_frame(pl.read_parquet(BytesIO(scores.payload_bytes)))
            evaluation = score_frame.join(threshold_frame.select("client_id", "threshold"), on="client_id", how="left")
            if evaluation["threshold"].null_count() > 0 and job.context.calibration_sample_count is None:
                raise ValueError("Threshold artifact does not cover every scored client")
            eligible = evaluation.filter(pl.col("threshold").is_not_null())
            if eligible.is_empty():
                metrics = _ineligible_client_metrics(evaluation)
            elif evaluation["threshold"].null_count() > 0:
                metrics = pl.concat((compute_operating_point_metrics(eligible), _ineligible_client_metrics(evaluation)))
            else:
                metrics = compute_operating_point_metrics(eligible)
            metrics = metrics.with_columns(
                pl.lit(job.context.threshold_policy_id.value if job.context.threshold_policy_id else None).alias(
                    "policy_id"
                ),
                pl.lit(job.context.seed).alias("seed"),
            )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        metrics.write_parquet(payload)
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "metric artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class StatisticalAnalysisStageHandler:
    """Persist configured paired seed analyses from immutable evaluation artifacts."""

    stage = StageKind.STATISTICAL_ANALYSIS

    def __init__(
        self, config: ResolvedProjectConfiguration, repository: ArtifactRepository, analysis: StatisticalAnalysisUseCase
    ) -> None:
        self._config = config
        self._repository = repository
        self._analysis = analysis

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        experiment = self._config.experiments.get(job.context.experiment_id)
        paired_analyses = tuple(item for item in experiment.analyses if isinstance(item, PairedThresholdAnalysisRecord))
        association_analyses = tuple(
            item for item in experiment.analyses if isinstance(item, MetricAssociationAnalysisRecord)
        )
        stability_analyses = tuple(
            item for item in experiment.analyses if isinstance(item, ThresholdStabilityAnalysisRecord)
        )
        if len(paired_analyses) + len(association_analyses) + len(stability_analyses) != len(experiment.analyses):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Statistical handler does not yet support every configured analysis kind",
            )
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        conditions = tuple(
            condition.name
            for sweep in experiment.sweeps
            if isinstance(sweep, ConditionSweepRecord)
            for condition in sweep.conditions
        ) or (None,)
        mu_sweep = experiment.training_overrides.get("mu") if experiment.training_overrides is not None else None
        mu_sweep_name = mu_sweep.get("from_sweep") if isinstance(mu_sweep, Mapping) else None
        mus = tuple(
            float(value)
            for sweep in experiment.sweeps
            if isinstance(sweep, ValueSweepRecord) and sweep.name == mu_sweep_name
            for value in sweep.values
            if isinstance(value, float)
        ) or (None,)
        training_profile = self._config.training_profiles.get(experiment.training_profile_id)
        ditto_weights = (
            training_profile.personalization_parameter_grid or (None,)
            if training_profile.personalization == "ditto"
            else (None,)
        )
        threshold_quantiles = tuple(
            float(value)
            for sweep in experiment.sweeps
            if isinstance(sweep, ValueSweepRecord) and sweep.name == "threshold_quantile"
            for value in sweep.values
            if isinstance(value, float)
        ) or (None,)
        shrinkage_weights = tuple(
            float(value)
            for sweep in experiment.sweeps
            if isinstance(sweep, ValueSweepRecord) and sweep.name == "shrinkage_weight"
            for value in sweep.values
            if isinstance(value, float)
        ) or (None,)
        calibration_sample_counts = _calibration_sample_counts(experiment)
        try:
            paired_results = [
                self._analyze_paired(
                    analysis,
                    experiment,
                    cohort.training_seeds,
                    run_id,
                    condition,
                    proximal_mu,
                    ditto_weight,
                    threshold_quantile,
                    shrinkage_weight,
                    calibration_sample_count,
                )
                for condition in conditions
                for proximal_mu in mus
                for ditto_weight in ditto_weights
                for threshold_quantile in threshold_quantiles
                for shrinkage_weight in shrinkage_weights
                for analysis in paired_analyses
                for calibration_sample_count in (
                    calibration_sample_counts if analysis.per_sweep_cell == "calibration_sample_count" else (None,)
                )
            ]
            results = paired_results + [
                self._analyze_association(analysis, paired_results, experiment, cohort.training_seeds, run_id)
                for analysis in association_analyses
            ]
            results.extend(
                self._analyze_threshold_stability(
                    analysis, experiment, cohort.training_seeds, run_id, calibration_sample_count
                )
                for analysis in stability_analyses
                for calibration_sample_count in calibration_sample_counts
            )
            training_profile = self._config.training_profiles.get(experiment.training_profile_id)
            if training_profile.kind == "federated_prox_training":
                results.append(self._federated_proximal_selection(experiment.identifier, run_id))
            if training_profile.personalization == "ditto":
                results.append(self._ditto_selection(experiment.identifier, run_id))
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = json.dumps(results, separators=(",", ":"), sort_keys=True).encode("utf-8")
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "statistical artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _analyze_paired(
        self,
        analysis: PairedThresholdAnalysisRecord,
        experiment,
        seeds,
        run_id: RunId,
        partition_condition: str | None,
        proximal_mu: float | None,
        ditto_weight: float | None,
        threshold_quantile: float | None,
        shrinkage_weight: float | None,
        calibration_sample_count: int | None,
    ) -> dict[str, object]:
        left = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.first_evaluation,
                analysis.primary_metric,
                run_id,
                partition_condition,
                proximal_mu,
                ditto_weight,
                threshold_quantile,
                shrinkage_weight,
                calibration_sample_count,
            )
            for seed in seeds
        )
        right = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.second_evaluation,
                analysis.primary_metric,
                run_id,
                partition_condition,
                proximal_mu,
                ditto_weight,
                threshold_quantile,
                shrinkage_weight,
                calibration_sample_count,
            )
            for seed in seeds
        )
        record = self._analysis.analyze_paired_seed_differences(
            left,
            right,
            analysis.primary_metric,
            self._evaluation_policy(experiment, analysis.first_evaluation),
            self._evaluation_policy(experiment, analysis.second_evaluation),
            analysis.statistical_profile,
            self._config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
        )
        result = {
            "analysis_label": analysis.label,
            "metric": record.metric_id.value,
            "first_threshold_policy": self._evaluation_policy(experiment, analysis.first_evaluation),
            "second_threshold_policy": self._evaluation_policy(experiment, analysis.second_evaluation),
            "first_seed_values": list(left),
            "second_seed_values": list(right),
            "first_mean": sum(left) / len(left),
            "second_mean": sum(right) / len(right),
            "mean_difference": record.mean_difference,
            "confidence_interval": [record.confidence_interval.lower_bound, record.confidence_interval.upper_bound],
            "p_value": None if record.hypothesis_test is None else record.hypothesis_test.p_value,
            "rank_biserial": record.effect_size,
            "resample_count": record.resample_count,
            "analysis_seed": record.analysis_seed.value,
        }
        if partition_condition is not None:
            result["partition_condition"] = partition_condition
        if proximal_mu is not None:
            result["federated_proximal_mu"] = proximal_mu
        if ditto_weight is not None:
            result["ditto_proximal_weight"] = ditto_weight
        if threshold_quantile is not None:
            result["threshold_quantile"] = threshold_quantile
        if shrinkage_weight is not None:
            result["shrinkage_weight"] = shrinkage_weight
        if calibration_sample_count is not None:
            result["calibration_sample_count"] = calibration_sample_count
        differences = [first - second for first, second in zip(left, right, strict=True)]
        result["seed_differences"] = differences
        result["sign_consistency"] = sum(value > 0.0 for value in differences) / len(differences)
        result["zero_difference_count"] = sum(value == 0.0 for value in differences)
        result["negative_difference_count"] = sum(value < 0.0 for value in differences)
        return result

    def _federated_proximal_selection(self, experiment_id, run_id: RunId) -> dict[str, object]:
        context = StageJobContext(experiment_id=experiment_id)
        relative_path = f"runs/{run_id.value}/{IdentityBuilder.federated_proximal_selection_job_id(context).value}"
        key = IdentityBuilder.federated_proximal_selection_key(context)
        if not self._repository.assess_reuse(
            relative_path,
            key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError("FedProx coefficient-selection artifact is unavailable or incompatible")
        artifact = self._repository.read(relative_path)
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError("FedProx coefficient-selection artifact is unreadable")
        payload = json.loads(artifact.payload_bytes)
        if not isinstance(payload, dict) or not isinstance(payload.get("selected_proximal_mu"), (int, float)):
            raise ValueError("FedProx coefficient-selection artifact is malformed")
        return {
            "analysis_label": "fedprox_primary_coefficient_selection",
            "selected_proximal_mu": float(payload["selected_proximal_mu"]),
            "locked_primary_round": payload.get("locked_primary_round"),
            "mean_benign_calibration_loss_by_mu": payload.get("mean_benign_calibration_loss_by_mu"),
        }

    def _ditto_selection(self, experiment_id, run_id: RunId) -> dict[str, object]:
        source = self._config.primary_ditto_selection_experiment()
        context = StageJobContext(experiment_id=source.identifier)
        source_run_id = (
            run_id
            if experiment_id == source.identifier
            else execution_run_id(source.identifier, self._config.execution_fingerprint.value)
        )
        relative_path = f"runs/{source_run_id.value}/{IdentityBuilder.ditto_selection_job_id(context).value}"
        key = IdentityBuilder.ditto_selection_key(context)
        if not self._repository.assess_reuse(
            relative_path,
            key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError("Ditto weight-selection artifact is unavailable or incompatible")
        artifact = self._repository.read(relative_path)
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError("Ditto weight-selection artifact is unreadable")
        payload = json.loads(artifact.payload_bytes)
        selected_weight = payload.get("selected_ditto_proximal_weight") if isinstance(payload, dict) else None
        if not isinstance(selected_weight, (int, float)):
            raise ValueError("Ditto weight-selection artifact is malformed")
        return {
            "analysis_label": "ditto_primary_proximal_weight_selection",
            "selected_ditto_proximal_weight": float(selected_weight),
            "locked_primary_round": payload.get("locked_primary_round"),
            "mean_benign_calibration_loss_by_weight": payload.get("mean_benign_calibration_loss_by_weight"),
        }

    def _analyze_association(
        self,
        analysis: MetricAssociationAnalysisRecord,
        paired_results: list[dict[str, object]],
        experiment,
        seeds,
        run_id: RunId,
    ) -> dict[str, object]:
        if analysis.predictor_metric != "pairwise_js_divergence" or analysis.outcome_metric != "cv_fpr_delta":
            raise ValueError(f"Unsupported association metrics for analysis '{analysis.label}'")
        source = [result for result in paired_results if result["analysis_label"] == analysis.outcome_source_analysis]
        if not source:
            raise ValueError(f"Association analysis '{analysis.label}' has no paired source analysis")
        observations: list[dict[str, float | int | str]] = []
        for result in source:
            condition = result.get("partition_condition")
            if not isinstance(condition, str):
                raise ValueError("Association analysis requires partition-conditioned paired results")
            differences = cast(list[float], result["seed_differences"])
            if len(differences) != len(seeds):
                raise ValueError("Association source has an incomplete paired seed cohort")
            for seed, difference in zip(seeds, differences, strict=True):
                observations.append(
                    {
                        "partition_condition": condition,
                        "seed": int(seed.value),
                        "pairwise_js_divergence": self._calibration_js(experiment, int(seed.value), condition, run_id),
                        "cv_fpr_delta": difference,
                    }
                )
        predictor = tuple(float(item["pairwise_js_divergence"]) for item in observations)
        outcome = tuple(float(item["cv_fpr_delta"]) for item in observations)
        spearman, regression = self._analysis.analyze_association(predictor, outcome)
        return {
            "analysis_label": analysis.label,
            "interpretation_constraint": analysis.interpretation_constraint,
            "spearman": {"coefficient": spearman.statistic, "p_value": spearman.p_value},
            "linear_regression": {
                "coefficient": regression.slope,
                "intercept": regression.intercept,
                "standard_error": regression.standard_error,
                "r_squared": regression.r_squared,
                "leverage": list(regression.leverage),
                "leave_one_out_slopes": list(regression.leave_one_out_slopes),
            },
            "observations": observations,
        }

    def _calibration_js(self, experiment, seed: int, partition_condition: str, run_id: RunId) -> float:
        context = StageJobContext(
            experiment_id=experiment.identifier, seed=seed, partition_condition=partition_condition
        )
        artifact = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(context).value}"
        )
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError(
                f"Calibration score artifact is unavailable for seed {seed}, condition '{partition_condition}'"
            )
        frame = validate_calibration_score_frame(pl.read_parquet(BytesIO(artifact.payload_bytes)))
        diagnostics = self._config.metric_definitions.heterogeneity_diagnostics.pairwise_js_divergence
        return calculate_pairwise_js_divergence(
            tuple(
                (ClientId(client[0]), tuple(float(value) for value in group["score"].to_list()))
                for client, group in frame.group_by("client_id", maintain_order=True)
            ),
            histogram_bins=diagnostics.histogram_bins,
            logarithm_base=diagnostics.logarithm_base,
        )

    def _evaluation_metric(
        self,
        experiment,
        seed: int,
        label: str,
        metric: str,
        run_id: RunId,
        partition_condition: str | None,
        proximal_mu: float | None,
        ditto_weight: float | None,
        threshold_quantile: float | None,
        shrinkage_weight: float | None,
        calibration_sample_count: int | None,
    ) -> float:
        if metric != "cv_fpr":
            raise ValueError(f"Statistical execution does not support configured metric '{metric}'")
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        overrides = evaluation.overrides or {}
        quantile_override = overrides.get("quantile")
        shrinkage_override = overrides.get("shrinkage_weight")
        policy = self._config.threshold_policies.get(evaluation.threshold_policy_id)
        quantile = threshold_quantile if isinstance(quantile_override, Mapping) else getattr(policy, "quantile", None)
        if not isinstance(quantile, float):
            raise ValueError(f"Evaluation '{label}' does not bind a quantile threshold policy")
        definition = self._config.metric_definitions.cross_client_aggregation.cv_fpr
        if definition.near_zero_mean_threshold_formula != "0.10 * (1 - evaluated_threshold_policy_quantile)":
            raise ValueError("CV(FPR) near-zero threshold formula is not the configured roadmap formula")
        replicates = (None,)
        if calibration_sample_count is not None:
            subset = experiment.calibration_subset
            if subset is None:
                raise ValueError("Calibration sample count is invalid for an experiment without a subset contract")
            replicates = tuple(range(subset.replicate_count.value))
        values: list[float] = []
        for replicate in replicates:
            context = StageJobContext(
                experiment_id=experiment.identifier,
                seed=seed,
                partition_condition=partition_condition,
                federated_proximal_mu=proximal_mu,
                ditto_proximal_weight=ditto_weight,
                threshold_quantile=threshold_quantile if isinstance(quantile_override, Mapping) else None,
                shrinkage_weight=shrinkage_weight if isinstance(shrinkage_override, Mapping) else None,
                calibration_sample_count=calibration_sample_count,
                calibration_replicate=replicate,
                evaluation_label=label,
            )
            artifact = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
            if not artifact.found or artifact.payload_bytes is None:
                raise ValueError(f"Evaluation artifact is unavailable for seed {seed}, label '{label}'")
            frame = validate_client_metric_frame(pl.read_parquet(BytesIO(artifact.payload_bytes)))
            fprs = tuple(
                float(value)
                for value in frame.filter(pl.col("false_positive_rate_status") == "available")[
                    "false_positive_rate"
                ].to_list()
            )
            dispersion = calculate_fpr_dispersion(
                fprs,
                cv_instability_threshold=0.10 * (1.0 - quantile),
                quantile_method="linear",
            )
            if dispersion.coefficient_of_variation.status is not MetricStatus.AVAILABLE:
                raise ValueError("Configured CV(FPR) is unavailable for paired statistical analysis")
            assert dispersion.coefficient_of_variation.value is not None
            values.append(dispersion.coefficient_of_variation.value)
        return sum(values) / len(values)

    def _analyze_threshold_stability(
        self,
        analysis: ThresholdStabilityAnalysisRecord,
        experiment,
        seeds,
        run_id: RunId,
        calibration_sample_count: int | None,
    ) -> dict[str, object]:
        if calibration_sample_count is None:
            raise ValueError("Threshold stability analysis requires a calibration sample-count sweep")
        subset = experiment.calibration_subset
        if subset is None or analysis.per_sweep_cell != "calibration_sample_count":
            raise ValueError(f"Threshold stability analysis '{analysis.label}' has an incompatible subset contract")
        evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
        policy = self._config.threshold_policies.get(evaluation.threshold_policy_id)
        quantile = getattr(policy, "quantile", None)
        if not isinstance(quantile, float):
            raise ValueError("Threshold stability analysis requires a quantile threshold policy")
        seed_results: list[dict[str, object]] = []
        for seed in seeds:
            threshold_values: dict[str, list[float]] = {}
            fpr_values: dict[str, list[float]] = {}
            for replicate in range(subset.replicate_count.value):
                context = StageJobContext(
                    experiment_id=experiment.identifier,
                    seed=seed.value,
                    calibration_sample_count=calibration_sample_count,
                    calibration_replicate=replicate,
                    evaluation_label=analysis.source_evaluation,
                )
                threshold_artifact = self._repository.read(
                    f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}"
                )
                metrics_artifact = self._repository.read(
                    f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}"
                )
                if (
                    not threshold_artifact.found
                    or threshold_artifact.payload_bytes is None
                    or not metrics_artifact.found
                    or metrics_artifact.payload_bytes is None
                ):
                    raise ValueError(f"Threshold stability artifacts are unavailable for seed {seed.value}")
                thresholds = validate_threshold_frame(pl.read_parquet(BytesIO(threshold_artifact.payload_bytes)))
                metrics = validate_client_metric_frame(pl.read_parquet(BytesIO(metrics_artifact.payload_bytes)))
                for client_id, threshold in thresholds.select("client_id", "threshold").iter_rows():
                    threshold_values.setdefault(str(client_id), []).append(float(threshold))
                for client_id, fpr in (
                    metrics.filter(pl.col("false_positive_rate_status") == "available")
                    .select("client_id", "false_positive_rate")
                    .iter_rows()
                ):
                    fpr_values.setdefault(str(client_id), []).append(float(fpr))
            test_context = StageJobContext(experiment_id=experiment.identifier, seed=seed.value)
            test_artifact = self._repository.read(
                f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(test_context).value}"
            )
            if not test_artifact.found or test_artifact.payload_bytes is None:
                raise ValueError(f"Test scores are unavailable for threshold stability seed {seed.value}")
            test_clients = set(
                validate_test_score_frame(pl.read_parquet(BytesIO(test_artifact.payload_bytes)))["client_id"]
            )
            variances = [
                sum((value - (sum(values) / len(values))) ** 2 for value in values) / len(values)
                for values in threshold_values.values()
            ]
            mean_fprs = [sum(values) / len(values) for values in fpr_values.values()]
            seed_results.append(
                {
                    "seed": seed.value,
                    "threshold_variance_across_replicates": sum(variances) / len(variances) if variances else None,
                    "absolute_attainment_error": (
                        sum(abs(value - (1.0 - quantile)) for value in mean_fprs) / len(mean_fprs)
                        if mean_fprs
                        else None
                    ),
                    "worst_client_fpr": max(mean_fprs) if mean_fprs else None,
                    "clients_unavailable_at_size": sorted(test_clients - set(threshold_values)),
                }
            )
        return {
            "analysis_label": analysis.label,
            "calibration_sample_count": calibration_sample_count,
            "replicate_aggregation": subset.replicate_aggregation_within_seed,
            "independent_inferential_unit": subset.independent_inferential_unit,
            "seed_results": seed_results,
        }

    @staticmethod
    def _evaluation_policy(experiment, label: str) -> str:
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        return evaluation.threshold_policy_id.value


class ResultFreezeStageHandler:
    """Close and validate immutable provenance before report rendering."""

    stage = StageKind.RESULT_FREEZE

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        statistics = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.statistical_analysis_job_id(job.context).value}"
        )
        if not statistics.found or statistics.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Statistical summary is unavailable"
            )
        experiment = self._config.experiments.get(job.context.experiment_id)
        try:
            profiles = tuple(self._config.report_profiles.get(identifier) for identifier in experiment.report_ids)
            payload = freeze_result_family(
                experiment=experiment,
                report_profiles=profiles,
                statistical_summary=statistics.payload_bytes,
                source_artifacts=job.inputs,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
            )
        except (KeyError, ResultFreezeError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "result-freeze artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class ReportGenerationStageHandler:
    """Render configured report artifacts exclusively from a frozen result manifest."""

    stage = StageKind.REPORT_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        result_freeze = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.result_freeze_job_id(job.context).value}"
        )
        if not result_freeze.found or result_freeze.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Result-freeze manifest is unavailable"
            )
        try:
            payload = render_frozen_report(result_freeze.payload_bytes)
        except ResultFreezeError as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        commit = _commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "report artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
