"""Outcome validation for graph-private jobs and declared semantic outputs."""

import pytest

from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.jobs import StageOutput
from datp_core.pipeline.stages.outcomes import StageJobOutcome


def _key(label: str = "test") -> GraphNodeKey:
    return GraphNodeKey(label=label)


def test_success_requires_declared_outputs() -> None:
    with pytest.raises(ValueError, match="produced outputs"):
        StageJobOutcome.succeeded(node_key=_key(), stage=StageKind.PREFLIGHT, produced_outputs=())


def test_failed_requires_error_message() -> None:
    with pytest.raises(ValueError, match="error message"):
        StageJobOutcome.failed(node_key=_key(), stage=StageKind.PREFLIGHT, error_message="")


def test_success_records_exact_declared_semantic_outputs() -> None:
    outputs = (StageOutput(name="resolved_configuration", relative_path="preflight/resolved-configuration.json"),)
    success = StageJobOutcome.succeeded(node_key=_key(), stage=StageKind.PREFLIGHT, produced_outputs=outputs)
    assert success.status is JobExecutionStatus.SUCCESS
    assert success.produced_outputs == outputs
    assert success.error_message is None
