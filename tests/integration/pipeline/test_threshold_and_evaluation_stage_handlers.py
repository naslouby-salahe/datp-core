"""End-to-end execution of the threshold-construction and operating-point-evaluation stage
handlers against synthetic calibration/test score artifacts, with a hand-verified B1 result.
"""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path

import polars as pl
import pytest

from datp_core.app import build_application
from datp_core.artifacts.codecs.manifest import CURRENT_ARTIFACT_SCHEMA_VERSION
from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey
from datp_core.artifacts.payloads import ArtifactCommitMetadata, ArtifactCommitRequest, BytesPayload
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.hashing import Fingerprint
from datp_core.core.identifiers import ClientId, ExperimentId, RunId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.evaluation.execution import OperatingPointEvaluationStageHandler
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import expand_experiment_jobs, score_context
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.thresholding.estimation.models import ClusterDiagnostics, ThresholdRecord, ThresholdSet
from datp_core.thresholding.execution.handler import (
    ThresholdConstructionStageHandler,
)
from datp_core.thresholding.policies.enums import ThresholdOwnerKind

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
    *,
    scientific_fingerprint: Fingerprint | None = None,
) -> None:
    payload = BytesIO()
    frame.write_parquet(payload)
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=ArtifactFormat.PARQUET,
                scientific_fingerprint=scientific_fingerprint or config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
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

    handler = ThresholdConstructionStageHandler(app.config, repository, app.construct_thresholds)
    outcome = handler.execute(job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    assert outcome.produced_artifact == job.output
    read = repository.read(f"runs/{run_id.value}/{job.job_id.value}")
    assert read.found and read.payload_bytes is not None
    thresholds = pl.read_parquet(BytesIO(read.payload_bytes))
    assert thresholds["policy_id"].unique().to_list() == ["shared_mean_p95"]
    assert thresholds["owner_kind"].unique().to_list() == ["shared_mean"]

    # `shared_mean_p95` never produces diagnostics, so replanning this stage must reuse the frozen
    # primary every time -- not fail because a diagnostics companion (that was never expected in
    # the first place) is absent.
    rerun_outcome = handler.execute(job, run_id)
    assert rerun_outcome.status is JobExecutionStatus.REUSED
    assert rerun_outcome.produced_artifact == job.output
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


def test_operating_point_evaluation_rejects_a_threshold_artifact_with_foreign_provenance(tmp_path: Path) -> None:
    """A threshold artifact physically present at the expected path but committed under a
    different scientific fingerprint (e.g. a stale artifact from an incompatible configuration)
    must be rejected before being read and parsed, not silently consumed."""
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
    foreign_fingerprint = Fingerprint("f" * 64)
    assert foreign_fingerprint != app.config.scientific_fingerprint
    _commit(
        repository,
        app.config,
        f"runs/{run_id.value}/{threshold_job.job_id.value}",
        threshold_job.output,
        pl.DataFrame(
            {
                "client_id": ["client_a"],
                "threshold": [1.0],
                "policy_id": ["shared_mean_p95"],
                "owner_kind": ["shared_mean"],
            }
        ),
        scientific_fingerprint=foreign_fingerprint,
    )
    test_score_context = score_context(eval_job.context)
    _commit(
        repository,
        app.config,
        f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(test_score_context).value}",
        IdentityBuilder.test_scores_key(test_score_context),
        pl.DataFrame({"client_id": ["client_a"], "score": [10.0], "label": [0]}),
    )

    outcome = OperatingPointEvaluationStageHandler(app.config, repository).execute(eval_job, run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message == "Threshold artifact is unavailable or incompatible"


class _FakeClusterThresholdsUseCase:
    """Stands in for the real clustering construction logic: always returns the identical
    deterministic threshold set, so this test can focus purely on the handler's resumable
    partial-family recovery for a diagnostics-*requiring* policy without exercising real
    clustering math."""

    def execute(self, *_args: object, **_kwargs: object) -> ThresholdSet:
        return ThresholdSet(
            policy_id=ThresholdPolicyId("cluster_k3_mean_p95"),
            values=(
                ThresholdRecord(
                    client_id=ClientId("client_a"),
                    threshold=5.0,
                    owner=ThresholdOwnerKind.LOCAL,
                    cluster_label=0,
                ),
            ),
            target_quantile=Probability(0.95),
            diagnostics=ClusterDiagnostics(cluster_count=1, cluster_labels=(("client_a", 0),)),
        )


def test_threshold_construction_resumes_a_matching_partial_family_missing_diagnostics(tmp_path: Path) -> None:
    """`cluster_k3_mean_p95` requires diagnostics. If the primary threshold frame is already
    frozen but the diagnostics companion is missing (e.g. a crash between the two commits), the
    handler must recompute, verify the primary matches deterministically, and complete the family
    by committing only the missing diagnostics -- not fail permanently."""
    app = build_application()
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    job = next(
        planned
        for planned in graph.jobs
        if planned.stage is StageKind.THRESHOLD_CONSTRUCTION
        and planned.context.seed == 0
        and planned.context.evaluation_label == "cluster_k3_mean"
    )
    assert job.context.threshold_policy_id is not None
    assert job.context.threshold_policy_id.value == "cluster_k3_mean_p95"
    run_id = RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    calibration_context = score_context(job.context, retain_calibration_subset=False)
    calibration_job_id = IdentityBuilder.calibration_score_job_id(calibration_context)
    _commit(
        repository,
        app.config,
        f"runs/{run_id.value}/{calibration_job_id.value}",
        IdentityBuilder.calibration_scores_key(calibration_context),
        pl.DataFrame({"client_id": ["client_a"] * 10, "score": list(_CLIENT_A_CALIBRATION)}),
    )
    handler = ThresholdConstructionStageHandler(
        app.config, repository, _FakeClusterThresholdsUseCase()  # type: ignore[arg-type]
    )

    first_outcome = handler.execute(job, run_id)
    assert first_outcome.status is JobExecutionStatus.SUCCESS
    diagnostics_relative = f"runs/{run_id.value}/{job.job_id.value}.diagnostics"
    assert repository.read(diagnostics_relative).found

    # Simulate a crash between the primary commit and the diagnostics commit: delete only the
    # diagnostics companion's on-disk directory, leaving the frozen primary untouched.
    diagnostics_dir = tmp_path / diagnostics_relative
    assert diagnostics_dir.is_dir()
    shutil.rmtree(diagnostics_dir)
    assert not repository.read(diagnostics_relative).found

    resumed_outcome = handler.execute(job, run_id)

    assert resumed_outcome.status is JobExecutionStatus.SUCCESS
    assert resumed_outcome.produced_artifact == job.output
    assert repository.read(diagnostics_relative).found
    # The primary artifact itself must never have been touched a second time.
    primary_read = repository.read(f"runs/{run_id.value}/{job.job_id.value}")
    assert primary_read.found and primary_read.payload_bytes is not None
    assert pl.read_parquet(BytesIO(primary_read.payload_bytes))["threshold"].to_list() == [5.0]
