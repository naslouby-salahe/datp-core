"""Outcome constructor validation and invalid-state rejection tests."""

import pytest

from datp_core.artifacts.models import ArtifactId, ArtifactKey, ArtifactKind
from datp_core.pipeline.identifiers import JobId
from datp_core.pipeline.models import JobExecutionStatus, StageJobOutcome, StageKind


def test_succeeded_requires_produced_artifact() -> None:
    with pytest.raises(TypeError):
        StageJobOutcome.succeeded(job_id=JobId("j1"), stage=StageKind.PREFLIGHT)  # type: ignore[call-arg]


def test_failed_requires_error_message() -> None:
    with pytest.raises(ValueError, match="error message"):
        StageJobOutcome.failed(job_id=JobId("j1"), stage=StageKind.PREFLIGHT, error_message="")

    with pytest.raises(TypeError):
        StageJobOutcome.failed(job_id=JobId("j1"), stage=StageKind.PREFLIGHT)  # type: ignore[call-arg]


def test_reused_requires_produced_artifact() -> None:
    with pytest.raises(TypeError):
        StageJobOutcome.reused(job_id=JobId("j1"), stage=StageKind.PREFLIGHT)  # type: ignore[call-arg]


def test_skipped_can_be_called_without_error_message() -> None:
    outcome = StageJobOutcome.skipped(job_id=JobId("j1"), stage=StageKind.PREFLIGHT)
    assert outcome.status is JobExecutionStatus.SKIPPED
    assert outcome.error_message is None


def test_suppressed_can_be_called_without_error_message() -> None:
    outcome = StageJobOutcome.suppressed(job_id=JobId("j1"), stage=StageKind.PREFLIGHT)
    assert outcome.status is JobExecutionStatus.SUPPRESSED
    assert outcome.error_message is None


def test_outcome_factory_correctness() -> None:
    key = ArtifactKey(artifact_id=ArtifactId("test_artifact"), kind=ArtifactKind.RESOLVED_CONFIG)

    success = StageJobOutcome.succeeded(job_id=JobId("j1"), stage=StageKind.PREFLIGHT, produced_artifact=key)
    assert success.status is JobExecutionStatus.SUCCESS
    assert success.produced_artifact == key
    assert success.error_message is None

    reused = StageJobOutcome.reused(job_id=JobId("j2"), stage=StageKind.PREFLIGHT, produced_artifact=key)
    assert reused.status is JobExecutionStatus.REUSED
    assert reused.produced_artifact == key
    assert reused.error_message is None

    failed = StageJobOutcome.failed(job_id=JobId("j3"), stage=StageKind.PREFLIGHT, error_message="something broke")
    assert failed.status is JobExecutionStatus.FAILED
    assert failed.produced_artifact is None
    assert failed.error_message == "something broke"

    skipped = StageJobOutcome.skipped(job_id=JobId("j4"), stage=StageKind.PREFLIGHT, error_message="not needed")
    assert skipped.status is JobExecutionStatus.SKIPPED
    assert skipped.produced_artifact is None
    assert skipped.error_message == "not needed"

    suppressed = StageJobOutcome.suppressed(job_id=JobId("j5"), stage=StageKind.PREFLIGHT, error_message="out of scope")
    assert suppressed.status is JobExecutionStatus.SUPPRESSED
    assert suppressed.produced_artifact is None
    assert suppressed.error_message == "out of scope"
