from inspect import getsource

from datp_core.pipeline.execution.engine import PipelineStageRunner
from datp_core.pipeline.feasibility import ExtensionKind, ExtensionRequest, assess_extension
from datp_core.protocols.graph import ObservationBoundary


def test_future_attack_behavior_is_not_implemented() -> None:
    decision = assess_extension(ExtensionRequest(kind=ExtensionKind.ATTACK, identity="poisoning"))
    assert not decision.permitted


def test_canonical_runner_invokes_every_declared_observation_boundary() -> None:
    source = getsource(PipelineStageRunner)
    for boundary in ObservationBoundary:
        assert f"ObservationBoundary.{boundary.name}" in source
