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
from datp_core.infrastructure.datasets.ciciot2023 import write_ciciot2023_materialized_parquet
from datp_core.infrastructure.datasets.nbaiot import (
    consolidate_nbaiot_parquet_sources,
    write_nbaiot_source_parquet,
)


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
    """Materialize configured N-BaIoT rows and commit the resulting Parquet artifact."""

    stage = StageKind.DATASET_MATERIALIZATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment_id = job.context.experiment_id
        experiment = self._config.experiments.get(experiment_id)
        population = self._config.populations.get(experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        if dataset.dataset_id.value not in {"nbaiot", "ciciot2023"}:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Dataset materializer is not implemented for this dataset",
            )
        primary_tree = dataset.inspection_contract.source_trees[0]
        benign_filename = dataset.inspection_contract.benign_filename
        if dataset.dataset_id.value == "nbaiot" and benign_filename is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="N-BaIoT configured benign filename is absent",
            )
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
        profile = self._config.runtime.active_execution_profile
        chunk_row_count = int(profile.data_loading.chunk_row_count)
        try:
            with TemporaryDirectory(prefix=f"datp_{dataset.dataset_id.value}_") as staging_directory:
                staging_root = Path(staging_directory)
                payload_file = staging_root / "materialized.parquet"
                if dataset.dataset_id.value == "nbaiot":
                    if benign_filename is None:
                        raise ValueError("N-BaIoT configured benign filename is absent")
                    staged_files = []
                    for source_index, source_path in enumerate(sorted(dataset.paths.raw_root.rglob("*.csv"))):
                        staged_file = staging_root / f"source_{source_index:04d}.parquet"
                        write_nbaiot_source_parquet(
                            source_path,
                            staged_file,
                            dataset.paths.raw_root,
                            primary_tree.required_headers,
                            benign_filename,
                            dataset.inspection_contract.attack_family_directories,
                            materialization,
                            chunk_row_count,
                        )
                        staged_files.append(staged_file)
                    consolidate_nbaiot_parquet_sources(tuple(staged_files), payload_file, chunk_row_count)
                else:
                    if dataset.inspection_contract.benign_label is None:
                        raise ValueError("CICIoT2023 configured benign label is absent")
                    merged_root = dataset.paths.raw_data_root / primary_tree.root.value
                    feature_headers = primary_tree.required_headers[:-1]
                    write_ciciot2023_materialized_parquet(
                        tuple(sorted(merged_root.glob(primary_tree.file_pattern))),
                        payload_file,
                        feature_headers,
                        primary_tree.required_headers[-1],
                        merged_root,
                        dataset.inspection_contract.benign_label,
                        materialization,
                        chunk_row_count,
                    )
                commit = self._repository.commit_file(
                    ArtifactFileCommitRequest(
                        artifact_key=job.output,
                        artifact_format=ArtifactFormat.PARQUET,
                        scientific_fingerprint=self._config.scientific_fingerprint,
                        execution_fingerprint=self._config.execution_fingerprint,
                        source_file=str(payload_file),
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
