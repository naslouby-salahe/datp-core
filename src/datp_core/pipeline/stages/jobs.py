"""Stage job with structural integrity invariants."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.artifacts.identity import ArtifactKey
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJob:
    node_key: StageNodeKey
    stage: StageKind
    context: StageJobContext
    inputs: tuple[ArtifactKey, ...]
    output: ArtifactKey
    dependencies: tuple[StageNodeKey, ...]

    def __post_init__(self) -> None:
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError(f"Job '{self.node_key.label}' has duplicate dependencies")
        if self.node_key in self.dependencies:
            raise ValueError(f"Job '{self.node_key.label}' cannot depend on itself")
        if len({a.node_key for a in self.inputs}) != len(self.inputs):
            raise ValueError(f"Job '{self.node_key.label}' has duplicate inputs")
        if self.output in self.inputs:
            raise ValueError(f"Job '{self.node_key.label}' output cannot appear in its inputs")
