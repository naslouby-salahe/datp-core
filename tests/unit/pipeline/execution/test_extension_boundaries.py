from inspect import getsource

from datp_core.pipeline.execution.engine import PipelineStageRunner
from datp_core.protocols.graph import ObservationBoundary


def test_canonical_runner_invokes_every_declared_observation_boundary() -> None:
    source = getsource(PipelineStageRunner)
    for boundary in ObservationBoundary:
        assert f"ObservationBoundary.{boundary.name}" in source
