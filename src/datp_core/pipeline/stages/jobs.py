"""Stage job with structural integrity invariants."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.artifacts.identity import ArtifactKey
from datp_core.core.identifiers import JobId
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJob:
    job_id: JobId
    stage: StageKind
    context: StageJobContext
    inputs: tuple[ArtifactKey, ...]
    output: ArtifactKey
    dependencies: tuple[JobId, ...]

    def __post_init__(self) -> None:
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError(f"Job '{self.job_id.value}' has duplicate dependencies")
        if self.job_id in self.dependencies:
            raise ValueError(f"Job '{self.job_id.value}' cannot depend on itself")
        if len({a.artifact_id for a in self.inputs}) != len(self.inputs):
            raise ValueError(f"Job '{self.job_id.value}' has duplicate inputs")
        if self.output in self.inputs:
            raise ValueError(f"Job '{self.job_id.value}' output cannot appear in its inputs")
