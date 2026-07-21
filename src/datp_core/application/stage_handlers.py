"""Application-facing stage-handler contracts and real preflight execution."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from typing import Protocol

import polars as pl
from safetensors.torch import load as load_safetensors
from safetensors.torch import save as save_safetensors

from datp_core.application.dataset_audit import AuditDatasetUseCase
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
from datp_core.domain.checkpoints import select_anchor_checkpoint_round, select_lowest_validation_loss_checkpoint
from datp_core.domain.identifiers import ArtifactId, ClientId, DatasetId, RunId
from datp_core.domain.outcomes import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.domain.thresholding import BenignCalibrationScores
from datp_core.domain.values import Seed
from datp_core.infrastructure.datasets.adapter_registry import DatasetAdapterRegistry
from datp_core.infrastructure.datasets.source_inventory import build_source_inventory
from datp_core.infrastructure.datasets.split_manifest import encode_split_manifest, read_materialized_split_evidence
from datp_core.infrastructure.learning.pytorch_adapter import (
    DynamicDenseAutoencoder,
    derive_model_initialization_seed,
    federated_train_autoencoder,
    load_benign_client_tensors,
    require_cuda_training_device,
    score_materialized_split,
    set_deterministic_seeds,
)
from datp_core.infrastructure.tables.polars_engine import compute_operating_point_metrics
from datp_core.infrastructure.tables.schemas import (
    validate_calibration_score_frame,
    validate_test_score_frame,
    validate_threshold_frame,
)
from datp_core.planning.identity import IdentityBuilder


class StageHandler(Protocol):
    """One executable stage that may only report success after an artifact commit."""

    stage: StageKind

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome: ...


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
        reuse = self._repository.assess_reuse(
            relative_path,
            job.output,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        )
        if reuse.can_reuse:
            companion_reusable = all(
                self._repository.assess_reuse(
                    companion_path,
                    companion_key,
                    self._config.scientific_fingerprint,
                    self._config.execution_fingerprint,
                ).can_reuse
                for companion_path, companion_key in (
                    (manifest_relative_path, manifest_key),
                    (readiness_relative_path, readiness_key),
                    (preprocessing_relative_path, preprocessing_key),
                )
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
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class ModelTrainingStageHandler:
    """Train one configured full-participation FedAvg model and persist its selected checkpoint."""

    stage = StageKind.MODEL_TRAINING

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        if profile.kind != "federated_averaging_training" or profile.participation != "full":
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=f"Training profile '{profile.identifier.value}' is not implemented by the FedAvg stage",
            )
        if job.context.seed is None or profile.local_epochs is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Training requires a seed and local epochs"
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
                result = federated_train_autoencoder(
                    DynamicDenseAutoencoder(
                        len(features.order), tuple(int(value.value) for value in architecture.hidden_dims)
                    ),
                    training_clients,
                    calibration_clients,
                    rounds=int(checkpoint_profile.total_rounds.value),
                    local_epochs=int(profile.local_epochs.value),
                    learning_rate=float(optimizer.learning_rate.value),
                    batch_size=int(batching.micro_batch_size.value),
                    seed=job.context.seed,
                    device=require_cuda_training_device(),
                    beta_1=optimizer.beta_1,
                    beta_2=optimizer.beta_2,
                    epsilon=float(optimizer.epsilon.value),
                    weight_decay=float(optimizer.weight_decay.value),
                    amsgrad=optimizer.amsgrad,
                    shuffle_each_epoch=batching.shuffle_each_epoch,
                    checkpoint_rounds=tuple(int(value.value) for value in checkpoint_profile.selected_rounds),
                    shuffle_seed_key=shuffle_namespace.key,
                    shuffle_seed_digest_bytes=digest_bytes,
                )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        if checkpoint_profile.convergence is not None:
            selected_round = select_anchor_checkpoint_round(
                convergence=checkpoint_profile.convergence,
                recorded_losses=result.round_losses,
                round_cap=int(checkpoint_profile.total_rounds.value),
            )
        else:
            selected_round = select_lowest_validation_loss_checkpoint(
                scheduled_rounds=tuple(int(value.value) for value in checkpoint_profile.selected_rounds),
                recorded_losses=result.round_losses,
            )
        selected = next(
            (checkpoint for checkpoint in result.scheduled_checkpoints if checkpoint.round_number == selected_round),
            None,
        )
        if selected is None:
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
            payload=BytesPayload(payload_bytes=save_safetensors(dict(selected.state))),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or "checkpoint commit failed"
            )
        selection_payload = json.dumps(
            {
                "schema_version": 1,
                "selected_round": selected_round,
                "round_losses": result.round_losses,
                "model_initialization_seed": initialization_seed,
                "dataloader_shuffle_seeds": [
                    [seed.round_number, seed.client_id, seed.local_epoch, seed.value]
                    for seed in result.derived_shuffle_seeds
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
        training_path = f"runs/{run_id.value}/{IdentityBuilder.training_job_id(job.context).value}"
        selection_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.inputs[0].artifact_id.value}:selection"),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )
        if not self._repository.assess_reuse(
            f"{training_path}.selection",
            selection_key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Selected-checkpoint evidence is unavailable or incompatible",
            )
        checkpoint = self._repository.read(training_path)
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
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
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
                model = DynamicDenseAutoencoder(
                    len(features.order), tuple(int(value.value) for value in architecture.hidden_dims)
                )
                model.load_state_dict(load_safetensors(checkpoint.payload_bytes))
                scores = score_materialized_split(
                    model,
                    materialized_path,
                    split=split,
                    feature_columns=features.order,
                    batch_size=int(batching.micro_batch_size.value),
                    device=require_cuda_training_device(),
                ).with_columns(
                    pl.lit(job.inputs[0].artifact_id.value).alias("checkpoint_artifact_id"),
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
            parents=_parents(self._config, (*job.inputs, selection_key)),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or "score artifact commit failed"
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


def _score_split(kind: ArtifactKind) -> str | None:
    if kind is ArtifactKind.CALIBRATION_SCORES:
        return "calibration"
    if kind is ArtifactKind.TEST_SCORES:
        return "test"
    return None


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
        calibration = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(job.context).value}"
        )
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
        if evaluation.overrides:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Sweep-derived threshold overrides require explicit expanded jobs",
            )
        try:
            scores = pl.read_parquet(BytesIO(calibration.payload_bytes))
            validate_calibration_score_frame(scores)
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
                None,
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
        scores = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(job.context).value}")
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
            if evaluation["threshold"].null_count() > 0:
                raise ValueError("Threshold artifact does not cover every scored client")
            metrics = compute_operating_point_metrics(evaluation).with_columns(
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
