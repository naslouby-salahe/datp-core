"""Dataset materialization: port contracts, adapter registry, and pipeline stage handlers.

The DatasetMaterializer/SourceInventory/MaterializationPayload Protocols and the adapter registry
live in the same module as the stage handlers that consume them -- resolving the former
application-layer/infrastructure-layer split (application/ports.py <-> infrastructure/datasets/
adapter_registry.py) that caused the app<->infra import cycle documented in CURRENT_ARCHITECTURE.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from attrs import define

from datp_core.artifacts.models import (
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
    FilePayload,
)
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.datasets.common import encode_split_manifest, read_materialized_split_evidence
from datp_core.datasets.discovery import build_source_inventory
from datp_core.datasets.models import (
    AdapterKind,
    ClientConstructionMethod,
    DatasetMaterialization,
    DatasetSetup,
    PartitionSeedContract,
    ResolvedDataset,
)
from datp_core.datasets.readiness import AuditDatasetUseCase, evaluate_readiness_gates
from datp_core.experiments.models import SweepConditionRecord
from datp_core.experiments.planning import resolve_partition_contract
from datp_core.pipeline.identifiers import DatasetId, RunId
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact


class SourceEntry(Protocol):
    """One ordered, typed source file entry produced by the source-discovery authority."""

    @property
    def source_path(self) -> Path: ...
    @property
    def relative_path(self) -> Path: ...
    @property
    def source_tree_identifier(self) -> str: ...


class SourceInventory(Protocol):
    """Ordered, typed inventory of source files for one resolved dataset.

    Materialization consumes this ordered inventory rather than discovering
    source files independently.
    """

    @property
    def dataset_id(self) -> DatasetId: ...
    @property
    def entries(self) -> tuple[SourceEntry, ...]: ...
    @property
    def file_count(self) -> int: ...


class MaterializationPayload(Protocol):
    """Result of a dataset adapter materializing one dataset to a staging directory."""

    @property
    def staged_path(self) -> Path: ...
    @property
    def row_count(self) -> int: ...
    @property
    def preprocessing_evidence(self) -> bytes: ...

    @property
    def partition_evidence(self) -> bytes | None: ...


class DatasetMaterializer(Protocol):
    """Port for materializing one resolved dataset to a staged Parquet payload.

    Each adapter implementation handles exactly one AdapterKind.
    """

    @property
    def adapter_kind(self) -> AdapterKind: ...

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
        *,
        chunk_row_count: int,
    ) -> MaterializationPayload: ...


@define(frozen=True, slots=True, kw_only=True)
class DatasetAdapterRegistry:
    """Immutable registry of dataset materializers indexed by AdapterKind."""

    adapters: dict[AdapterKind, DatasetMaterializer]

    def get(self, kind: AdapterKind) -> DatasetMaterializer:
        """Return the adapter registered for the given AdapterKind.

        Raises KeyError if no adapter is registered (missing-adapter error).
        """
        try:
            return self.adapters[kind]
        except KeyError:
            raise KeyError(
                f"No dataset materializer registered for adapter kind '{kind.value}'. "
                f"Registered kinds: {[k.value for k in self.adapters]}"
            ) from None

    @property
    def registered_kinds(self) -> tuple[AdapterKind, ...]:
        return tuple(self.adapters.keys())


class PreflightStageHandler:
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
        commit = commit_artifact(
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
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
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
            if setup.client_construction.method == ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS
            else None
        )
        try:
            partition_condition, partition_seed_contract = resolve_partition_contract(
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
                    chunk_row_count=self._config.runtime.active_execution_profile.data_loading.chunk_row_count.value,
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
                gate_issues = evaluate_readiness_gates(
                    experiment.readiness_gates,
                    self._config.eligibility_gates,  # type: ignore[arg-type]
                    split_evidence.manifest,
                    experiment.identifier,
                )
                if gate_issues:
                    return StageJobOutcome.infeasible(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message="Eligibility gate(s) failed: " + "; ".join(gate_issues),
                    )
                split_manifest_payload = encode_split_manifest(split_evidence.manifest)
                commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=job.output,
                    artifact_format=ArtifactFormat.PARQUET,
                    relative_path=relative_path,
                    parents=artifact_parents(self._config, job.inputs),
                    payload=FilePayload(source_file=str(payload.staged_path)),
                )
                if not commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=commit.error_message or "materialized artifact commit failed",
                    )
                manifest_commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=manifest_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=manifest_relative_path,
                    parents=artifact_parents(self._config, (job.output,)),
                    payload=BytesPayload(payload_bytes=split_manifest_payload),
                )
                if not manifest_commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=manifest_commit.error_message or "split manifest commit failed",
                    )
                readiness_commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=readiness_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=readiness_relative_path,
                    parents=artifact_parents(self._config, (job.output,)),
                    payload=BytesPayload(payload_bytes=readiness.encode()),
                )
                if not readiness_commit.success:
                    return StageJobOutcome.failed(
                        job_id=job.job_id,
                        stage=job.stage,
                        error_message=readiness_commit.error_message or "dataset readiness commit failed",
                    )
                preprocessing_commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=preprocessing_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=preprocessing_relative_path,
                    parents=artifact_parents(self._config, (job.output,)),
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
                    partition_commit = commit_artifact(
                        self._repository,
                        self._config,
                        job.context,
                        artifact_key=partition_key,
                        artifact_format=ArtifactFormat.JSON,
                        relative_path=partition_relative_path,
                        parents=artifact_parents(self._config, (job.output,)),
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
