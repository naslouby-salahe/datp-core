"""Stage handler protocol and registry.

Each stage handler receives a StageJob and must produce a StageJobOutcome.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


@runtime_checkable
class StageHandler(Protocol):
    """Protocol for a handler that executes one pipeline stage.

    Handlers are stateless: the same handler instance must be safe to call
    concurrently for different jobs of the same StageKind.
    """

    stage: StageKind

    def execute(self, job: StageJob) -> StageJobOutcome: ...
