"""CalibrationSubsamplingStageHandler executed against a synthetic calibration score artifact.

Directly verifies the roadmap's nested-window invariant (roadmap 05 calibration-window-size
stability contract): the deterministic subset at a smaller requested size must be an exact
prefix of the subset at every larger requested size for the same seed and replicate.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import polars as pl

from datp_core.experiments.sweeps import score_context
from datp_core.thresholding.calibration import CalibrationSubsamplingStageHandler
from datp_core.bootstrap import DatpApplication, build_application
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    BytesPayload,
)
from datp_core.pipeline.identifiers import ExperimentId, RunId
from datp_core.pipeline.models import JobExecutionStatus, StageJob, StageKind
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.thresholding.calibration import subsample_calibration_scores
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.experiments.identity import IdentityBuilder

_EXPERIMENT_ID = ExperimentId("calibration_window_size_stability")


def _jobs(app: DatpApplication) -> dict[int | None, StageJob]:
    graph = expand_experiment_jobs(app.config.experiments.get(_EXPERIMENT_ID), app.config)
    matches = [
        job
        for job in graph.jobs
        if job.stage is StageKind.CALIBRATION_SUBSAMPLING
        and job.context.seed == 0
        and job.context.calibration_replicate == 0
    ]
    return {job.context.calibration_sample_count: job for job in matches}


def _run_id(app: DatpApplication) -> RunId:
    return RunId(f"run_calibration_window_size_stability_{app.config.execution_fingerprint.value[:12]}")


def _calibration_frame(row_count: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "client_id": ["client_a"] * row_count,
            "source_path": ["client_a.csv"] * row_count,
            "source_row_index": list(range(row_count)),
            "score": [float(index) / row_count for index in range(row_count)],
        }
    )


def _commit_calibration_scores(
    repository: AtomicArtifactRepository,
    app: DatpApplication,
    run_id: RunId,
    job: StageJob,
    row_count: int,
) -> None:
    calibration_context = score_context(job.context)
    calibration_job_id = IdentityBuilder.calibration_score_job_id(calibration_context)
    payload = BytesIO()
    _calibration_frame(row_count).write_parquet(payload)
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=job.inputs[0],
                artifact_format=ArtifactFormat.PARQUET,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=f"runs/{run_id.value}/{calibration_job_id.value}",
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
    )
    assert result.success, result.error_message


def test_smaller_window_is_an_exact_prefix_of_the_larger_window(tmp_path: Path) -> None:
    app = build_application()
    jobs = _jobs(app)
    run_id = _run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    # client_a has exactly 100 benign calibration rows: eligible for both requested sizes.
    # Both jobs share the same calibration-score input artifact; commit it once.
    _commit_calibration_scores(repository, app, run_id, jobs[50], row_count=100)

    outcome_50 = CalibrationSubsamplingStageHandler(app.config, repository).execute(jobs[50], run_id)
    outcome_100 = CalibrationSubsamplingStageHandler(app.config, repository).execute(jobs[100], run_id)

    assert outcome_50.status is JobExecutionStatus.SUCCESS
    assert outcome_100.status is JobExecutionStatus.SUCCESS
    read_50 = repository.read(f"runs/{run_id.value}/{jobs[50].job_id.value}")
    read_100 = repository.read(f"runs/{run_id.value}/{jobs[100].job_id.value}")
    assert read_50.payload_bytes is not None and read_100.payload_bytes is not None
    subset_50 = pl.read_parquet(read_50.payload_bytes)
    subset_100 = pl.read_parquet(read_100.payload_bytes)
    assert subset_50.height == 50
    assert subset_100.height == 100
    rows_50 = set(subset_50["source_row_index"].to_list())
    rows_100 = set(subset_100["source_row_index"].to_list())
    assert rows_50.issubset(rows_100)


def test_result_matches_direct_call_to_the_deterministic_sampler(tmp_path: Path) -> None:
    app = build_application()
    jobs = _jobs(app)
    run_id = _run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    job = jobs[50]
    frame = _calibration_frame(100)
    _commit_calibration_scores(repository, app, run_id, job, row_count=100)
    experiment = app.config.experiments.get(_EXPERIMENT_ID)
    subset_contract = experiment.calibration_subset
    assert subset_contract is not None
    namespace = app.config.protocol_determinism.seed_namespaces["calibration_subsample"]
    digest_bytes = int(app.config.protocol_determinism.derived_seed_algorithm["digest_bytes"])
    expected = subsample_calibration_scores(
        frame,
        requested_sample_count=50,
        training_seed=0,
        selection_seed=subset_contract.selection_seed.value,
        replicate=0,
        namespace_key=namespace.key,
        digest_bytes=digest_bytes,
    )

    outcome = CalibrationSubsamplingStageHandler(app.config, repository).execute(job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    read = repository.read(f"runs/{run_id.value}/{job.job_id.value}")
    assert read.payload_bytes is not None
    produced = pl.read_parquet(read.payload_bytes)
    assert produced.sort("source_row_index").to_dicts() == expected.sort("source_row_index").to_dicts()


def test_calibration_subsampling_reuses_a_frozen_subset(tmp_path: Path) -> None:
    app = build_application()
    jobs = _jobs(app)
    run_id = _run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    job = jobs[50]
    _commit_calibration_scores(repository, app, run_id, job, row_count=100)
    handler = CalibrationSubsamplingStageHandler(app.config, repository)
    first = handler.execute(job, run_id)
    assert first.status is JobExecutionStatus.SUCCESS
    first_bytes = repository.read(f"runs/{run_id.value}/{job.job_id.value}").payload_bytes

    second = handler.execute(job, run_id)

    assert second.status is JobExecutionStatus.REUSED
    assert repository.read(f"runs/{run_id.value}/{job.job_id.value}").payload_bytes == first_bytes


def test_calibration_subsampling_fails_typed_when_calibration_scores_are_unavailable(tmp_path: Path) -> None:
    app = build_application()
    jobs = _jobs(app)
    run_id = _run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)

    outcome = CalibrationSubsamplingStageHandler(app.config, repository).execute(jobs[50], run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message == "Calibration score artifact is unavailable"
