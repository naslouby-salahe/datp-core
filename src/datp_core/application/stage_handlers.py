"""Application-facing stage-handler contracts and real preflight execution."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from typing import Protocol

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactCommitRequest,
    ArtifactFileCommitRequest,
    ArtifactFormat,
    ArtifactParent,
    ArtifactRepository,
)
from datp_core.domain.identifiers import DatasetId, RunId
from datp_core.domain.outcomes import StageJob, StageJobOutcome, StageKind
from datp_core.infrastructure.datasets.adapter_registry import DatasetAdapterRegistry
from datp_core.infrastructure.datasets.source_inventory import build_source_inventory


class StageHandler(Protocol):
    """One executable stage that may only report success after an artifact commit."""

    stage: StageKind

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome: ...


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
                "scientific_fingerprint": self._config.scientific_fingerprint.value,
                "execution_fingerprint": self._config.execution_fingerprint.value,
            },
            sort_keys=True,
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
        commit = self._repository.commit(
            ArtifactCommitRequest(
                artifact_key=job.output,
                artifact_format=ArtifactFormat.JSON,
                scientific_fingerprint=self._config.scientific_fingerprint,
                execution_fingerprint=self._config.execution_fingerprint,
                payload_bytes=payload,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=time(),
                environment_identity="runtime_bootstrap",
            )
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
                commit = self._repository.commit_file(
                    ArtifactFileCommitRequest(
                        artifact_key=job.output,
                        artifact_format=ArtifactFormat.PARQUET,
                        scientific_fingerprint=self._config.scientific_fingerprint,
                        execution_fingerprint=self._config.execution_fingerprint,
                        source_file=str(payload.staged_path),
                        relative_path=relative_path,
                        parents=tuple(
                            ArtifactParent(
                                parent_key=input_artifact,
                                scientific_fingerprint=self._config.scientific_fingerprint,
                            )
                            for input_artifact in job.inputs
                        ),
                        schema_version=1,
                        creation_timestamp=time(),
                        environment_identity="runtime_bootstrap",
                    )
                )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        return (
            StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
            if commit.success
            else StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or "artifact commit failed"
            )
        )
