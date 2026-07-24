"""Outcome constructor validation and invalid-state rejection tests."""

import pytest

from datp_core.artifacts.identity import ArtifactKey, ArtifactKind
from datp_core.core.identifiers import ExperimentId
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey
from datp_core.pipeline.stages.outcomes import StageJobOutcome


def _key(label: str = "test_artifact") -> StageNodeKey:
    return StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT, seed=hash(label) % 1000)


def test_succeeded_requires_produced_artifact() -> None:
    with pytest.raises(TypeError):
        StageJobOutcome.succeeded(node_key=_key("j1"), stage=StageKind.PREFLIGHT)  # type: ignore[call-arg]


def test_failed_requires_error_message() -> None:
    with pytest.raises(ValueError, match="error message"):
        StageJobOutcome.failed(node_key=_key("j1"), stage=StageKind.PREFLIGHT, error_message="")

    with pytest.raises(TypeError):
        StageJobOutcome.failed(node_key=_key("j1"), stage=StageKind.PREFLIGHT)  # type: ignore[call-arg]


def test_skipped_can_be_called_without_error_message() -> None:
    outcome = StageJobOutcome.skipped(node_key=_key("j1"), stage=StageKind.PREFLIGHT)
    assert outcome.status is JobExecutionStatus.SKIPPED
    assert outcome.error_message is None


def test_suppressed_can_be_called_without_error_message() -> None:
    outcome = StageJobOutcome.suppressed(node_key=_key("j1"), stage=StageKind.PREFLIGHT)
    assert outcome.status is JobExecutionStatus.SUPPRESSED
    assert outcome.error_message is None


def test_outcome_factory_correctness() -> None:
    key = ArtifactKey(node_key=_key("test_artifact"), kind=ArtifactKind.RESOLVED_CONFIG)

    success = StageJobOutcome.succeeded(node_key=_key("j1"), stage=StageKind.PREFLIGHT, produced_artifact=key)
    assert success.status is JobExecutionStatus.SUCCESS
    assert success.produced_artifact == key
    assert success.error_message is None

    failed = StageJobOutcome.failed(node_key=_key("j3"), stage=StageKind.PREFLIGHT, error_message="something broke")
    assert failed.status is JobExecutionStatus.FAILED
    assert failed.produced_artifact is None
    assert failed.error_message == "something broke"

    skipped = StageJobOutcome.skipped(node_key=_key("j4"), stage=StageKind.PREFLIGHT, error_message="not needed")
    assert skipped.status is JobExecutionStatus.SKIPPED
    assert skipped.produced_artifact is None
    assert skipped.error_message == "not needed"

    suppressed = StageJobOutcome.suppressed(node_key=_key("j5"), stage=StageKind.PREFLIGHT, error_message="out of scope")
    assert suppressed.status is JobExecutionStatus.SUPPRESSED
    assert suppressed.produced_artifact is None
    assert suppressed.error_message == "out of scope"
