"""Stage-handler protocol."""

from __future__ import annotations

from typing import Protocol

from datp_core.core.identifiers import RunId
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class StageHandler(Protocol):
    stage: StageKind

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome: ...
