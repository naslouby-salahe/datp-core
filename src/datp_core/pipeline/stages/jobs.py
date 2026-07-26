"""Typed active-run stage jobs with explicit semantic file locations."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind


def _require_relative_path(path: str) -> None:
    normalized = path.replace("\\", "/")
    if not path or normalized.startswith("/") or ":" in normalized.split("/")[0] or ".." in normalized.split("/"):
        raise ValueError(f"Stage paths must be safe relative paths: {path!r}")


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisInputCoordinates:
    """Exact scientific coordinates of an artifact supplied to statistical analysis."""

    producer_stage: StageKind
    output_name: str
    context: StageJobContext

    def __post_init__(self) -> None:
        if not self.output_name:
            raise ValueError("Analysis input coordinates require an output name")


@dataclass(frozen=True, slots=True, kw_only=True)
class StageInput:
    """One named direct dependency file supplied by the planner."""

    name: str
    relative_path: str
    producer: GraphNodeKey
    coordinates: AnalysisInputCoordinates | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A stage input requires a name")
        _require_relative_path(self.relative_path)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageOutput:
    """One named semantic file produced by a stage in this execution."""

    name: str
    relative_path: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A stage output requires a name")
        _require_relative_path(self.relative_path)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJob:
    node_key: GraphNodeKey
    stage: StageKind
    context: StageJobContext
    inputs: tuple[StageInput, ...]
    outputs: tuple[StageOutput, ...]
    dependencies: tuple[GraphNodeKey, ...]

    def __post_init__(self) -> None:
        dependency_keys = frozenset(self.dependencies)
        if len(dependency_keys) != len(self.dependencies):
            raise ValueError(f"Job '{self.node_key.label}' has duplicate dependencies")
        if self.node_key in dependency_keys:
            raise ValueError(f"Job '{self.node_key.label}' cannot depend on itself")
        if not self.outputs:
            raise ValueError(f"Job '{self.node_key.label}' must declare at least one output")
        if len({item.name for item in self.inputs}) != len(self.inputs):
            raise ValueError(f"Job '{self.node_key.label}' has duplicate inputs")
        if len({item.name for item in self.outputs}) != len(self.outputs):
            raise ValueError(f"Job '{self.node_key.label}' has duplicate outputs")
        if len({item.relative_path for item in self.outputs}) != len(self.outputs):
            raise ValueError(f"Job '{self.node_key.label}' has duplicate output paths")
        if any(item.producer not in dependency_keys for item in self.inputs):
            raise ValueError(
                f"Job '{self.node_key.label}' has an input without a direct dependency")
        if self.stage is StageKind.STATISTICAL_ANALYSIS and any(item.coordinates is None for item in self.inputs):
            raise ValueError(
                f"Statistical job '{self.node_key.label}' requires typed analysis input coordinates")

    def input_path(self, name: str) -> str:
        return next(item.relative_path for item in self.inputs if item.name == name)

    def output_path(self, name: str) -> str:
        return next(item.relative_path for item in self.outputs if item.name == name)
