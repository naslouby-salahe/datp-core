"""End-to-end execution of the threshold-construction and operating-point-evaluation stage
handlers against synthetic calibration/test score artifacts, with a hand-verified B1 result.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import polars as pl
import pytest

from datp_core.app import build_application
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    BytesPayload,
)
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.evaluation.execution import OperatingPointEvaluationStageHandler
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import expand_experiment_jobs, score_context
from datp_core.pipeline.models import JobExecutionStatus, StageKind
from datp_core.thresholding.construction import (
    ThresholdConstructionStageHandler,
)

_CLIENT_A_CALIBRATION = tuple(float(value) for value in range(1, 11))
_CLIENT_B_CALIBRATION = tuple(float(value) * 10 for value in range(1, 11))
# np.quantile(..., 0.95, method="linear") on 10 sorted values interpolates between index 8 and 9.
_CLIENT_A_P95 = 9.55
_CLIENT_B_P95 = 95.5
_EXPECTED_SHARED_MEAN_THRESHOLD = (_CLIENT_A_P95 + _CLIENT_B_P95) / 2


def _commit(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    relative_path: str,
    artifact_key: ArtifactKey,
    frame: pl.DataFrame,
) -> None:
    payload = BytesIO()
    frame.write_parquet(payload)
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=ArtifactFormat.PARQUET,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
    )
    assert result.success, result.error_message


def test_threshold_construction_computes_the_exact_shared_mean_of_client_quantiles(tmp_path: Path) -> None:
    app = build_application()
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    job = next(
        planned
        for planned in graph.jobs
        if planned.stage is StageKind.THRESHOLD_CONSTRUCTION and planned.context.seed == 0
    )
    assert job.context.threshold_policy_id is not None
    assert job.context.threshold_policy_id.value == "shared_mean_p95"
    run_id = RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    calibration_context = score_context(job.context, retain_calibration_subset=False)
    calibration_job_id = IdentityBuilder.calibration_score_job_id(calibration_context)
    calibration_frame = pl.DataFrame(
        {
            "client_id": ["client_a"] * 10 + ["client_b"] * 10,
            "score": list(_CLIENT_A_CALIBRATION) + list(_CLIENT_B_CALIBRATION),
        }
    )
    _commit(
        repository,
        app.config,
        f"runs/{run_id.value}/{calibration_job_id.value}",
        IdentityBuilder.calibration_scores_key(calibration_context),
        calibration_frame,
    )

    outcome = ThresholdConstructionStageHandler(app.config, repository, app.construct_thresholds).execute(job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    assert outcome.produced_artifact == job.output
    read = repository.read(f"runs/{run_id.value}/{job.job_id.value}")
    assert read.found and read.payload_bytes is not None
    thresholds = pl.read_parquet(BytesIO(read.payload_bytes))
    assert thresholds["policy_id"].unique().to_list() == ["shared_mean_p95"]
    assert thresholds["owner_kind"].unique().to_list() == ["shared_mean"]
    for value in thresholds["threshold"].to_list():
        assert value == pytest.approx(_EXPECTED_SHARED_MEAN_THRESHOLD)


def test_operating_point_evaluation_computes_exact_confusion_counts(tmp_path: Path) -> None:
    app = build_application()
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    threshold_job = next(
        planned
        for planned in graph.jobs
        if planned.stage is StageKind.THRESHOLD_CONSTRUCTION and planned.context.seed == 0
    )
    eval_job = next(
        planned
        for planned in graph.jobs
        if planned.stage is StageKind.OPERATING_POINT_EVALUATION and planned.context.seed == 0
    )
    run_id = RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    calibration_context = score_context(threshold_job.context, retain_calibration_subset=False)
    calibration_job_id = IdentityBuilder.calibration_score_job_id(calibration_context)
    calibration_frame = pl.DataFrame(
        {
            "client_id": ["client_a"] * 10 + ["client_b"] * 10,
            "score": list(_CLIENT_A_CALIBRATION) + list(_CLIENT_B_CALIBRATION),
        }
    )
    _commit(
        repository,
        app.config,
        f"runs/{run_id.value}/{calibration_job_id.value}",
        IdentityBuilder.calibration_scores_key(calibration_context),
        calibration_frame,
    )
    threshold_outcome = ThresholdConstructionStageHandler(app.config, repository, app.construct_thresholds).execute(
        threshold_job, run_id
    )
    assert threshold_outcome.status is JobExecutionStatus.SUCCESS

    test_score_context = score_context(eval_job.context)
    test_score_job_id = IdentityBuilder.test_score_job_id(test_score_context)
    # Threshold is _EXPECTED_SHARED_MEAN_THRESHOLD (52.525) for both clients.
    # client_a: one score below (benign, correctly rejected) and one above (attack, correctly flagged).
    # client_b: one score above (benign, false positive) and one below (attack, false negative).
    test_frame = pl.DataFrame(
        {
            "client_id": ["client_a", "client_a", "client_b", "client_b"],
            "score": [10.0, 60.0, 60.0, 10.0],
            "label": [0, 1, 0, 1],
        }
    )
    _commit(
        repository,
        app.config,
        f"runs/{run_id.value}/{test_score_job_id.value}",
        IdentityBuilder.test_scores_key(test_score_context),
        test_frame,
    )

    outcome = OperatingPointEvaluationStageHandler(app.config, repository).execute(eval_job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    read = repository.read(f"runs/{run_id.value}/{eval_job.job_id.value}")
    assert read.found and read.payload_bytes is not None
    metrics = pl.read_parquet(BytesIO(read.payload_bytes)).sort("client_id")
    client_a = metrics.filter(pl.col("client_id") == "client_a").row(0, named=True)
    client_b = metrics.filter(pl.col("client_id") == "client_b").row(0, named=True)
    assert client_a["true_negatives"] == 1
    assert client_a["true_positives"] == 1
    assert client_a["false_positives"] == 0
    assert client_a["false_negatives"] == 0
    assert client_a["false_positive_rate"] == 0.0
    assert client_a["true_positive_rate"] == 1.0
    assert client_b["false_positives"] == 1
    assert client_b["true_negatives"] == 0
    assert client_b["false_negatives"] == 1
    assert client_b["true_positives"] == 0
    assert client_b["false_positive_rate"] == 1.0
    assert client_b["true_positive_rate"] == 0.0
