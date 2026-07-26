"""Typed analysis artifact repository.

Analysis capabilities request domain artifacts, not bytes or arbitrary relative paths.
Schema validation occurs before returning any artifact.

Path resolution is handled by a private ``_ArtifactPathIndex`` that maps
``AnalysisInputCoordinates`` to relative paths, replacing the former
``AnalysisInputBundle``.
"""

from __future__ import annotations

from io import BytesIO
from types import MappingProxyType

import polars as pl

from datp_core.analysis.errors import ArtifactMissingError, ArtifactSchemaViolationError
from datp_core.artifacts.errors import ArtifactFileMissingError
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame, validate_test_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput


class _ArtifactPathIndex:
    """Immutable exact-coordinate index over declared stage inputs.

    Replaces ``AnalysisInputBundle`` from ``execution/inputs.py``.
    """

    def __init__(self, artifacts: tuple) -> None:
        by_coordinates = {artifact.coordinates: artifact.relative_path for artifact in artifacts}
        if len(by_coordinates) != len(artifacts):
            raise ArtifactSchemaViolationError("Statistical analysis has duplicate artifact coordinates")
        self._paths: MappingProxyType = MappingProxyType(by_coordinates)

    @classmethod
    def from_stage_inputs(cls, inputs: tuple[StageInput, ...]) -> _ArtifactPathIndex:
        from datp_core.analysis.contracts import AnalysisArtifactRef

        artifact_refs: list = []
        for item in inputs:
            if item.coordinates is None:
                raise ArtifactMissingError(f"Analysis input '{item.name}' lacks typed coordinates")
            artifact_refs.append(AnalysisArtifactRef(coordinates=item.coordinates, relative_path=item.relative_path))
        return cls(tuple(artifact_refs))

    def resolve(self, *, producer_stage: StageKind, output_name: str, context: StageJobContext) -> str:
        coordinates = AnalysisInputCoordinates(
            producer_stage=producer_stage,
            output_name=output_name,
            context=context,
        )
        try:
            return self._paths[coordinates]
        except KeyError:
            raise ArtifactMissingError(
                f"Analysis input not declared: stage={producer_stage.value}, "
                f"output={output_name}, context={context}"
            ) from None

    def evaluation_metrics(self, context: StageJobContext) -> str:
        return self.resolve(
            producer_stage=StageKind.OPERATING_POINT_EVALUATION,
            output_name="client_metrics",
            context=context,
        )

    def thresholds(self, context: StageJobContext) -> str:
        return self.resolve(
            producer_stage=StageKind.THRESHOLD_CONSTRUCTION,
            output_name="thresholds",
            context=context,
        )

    def calibration_scores(self, context: StageJobContext) -> str:
        return self.resolve(
            producer_stage=StageKind.SCORE_GENERATION,
            output_name="calibration_scores",
            context=context,
        )

    def test_scores(self, context: StageJobContext) -> str:
        return self.resolve(
            producer_stage=StageKind.SCORE_GENERATION,
            output_name="test_scores",
            context=context,
        )

    def checkpoint(self, context: StageJobContext) -> str:
        return self.resolve(
            producer_stage=StageKind.MODEL_TRAINING,
            output_name="checkpoint",
            context=context,
        )

    def checkpoint_selection(self, context: StageJobContext) -> str:
        return self.resolve(
            producer_stage=StageKind.CHECKPOINT_SELECTION,
            output_name="checkpoint_selection",
            context=context,
        )


AnalysisInputBundle = _ArtifactPathIndex


class AnalysisArtifactRepository:
    """Typed access to validated analysis artifacts backed by an ArtifactStore."""

    def __init__(self, store: ArtifactStore, path_index: _ArtifactPathIndex | None = None) -> None:
        self._store = store
        self._path_index = path_index

    @property
    def store(self) -> ArtifactStore:
        return self._store

    # -- path-based API (backward compatibility during migration) ----------

    def threshold_frame(self, relative_path: str) -> pl.DataFrame:
        return self._read_validated(relative_path, validate_threshold_frame, "threshold")

    def calibration_score_frame(self, relative_path: str) -> pl.DataFrame:
        return self._read_validated(relative_path, validate_calibration_score_frame, "calibration score")

    def test_score_frame(self, relative_path: str) -> pl.DataFrame:
        return self._read_validated(relative_path, validate_test_score_frame, "test score")

    def client_metric_frame(self, relative_path: str) -> pl.DataFrame:
        return self._read_validated(relative_path, validate_client_metric_frame, "client metric")

    def threshold_and_calibration_frames(
        self, threshold_path: str, calibration_score_path: str
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        return (
            self.threshold_frame(threshold_path),
            self.calibration_score_frame(calibration_score_path),
        )

    def read_bytes(self, relative_path: str) -> bytes:
        try:
            return self._store.read_bytes(relative_path)
        except ArtifactFileMissingError:
            raise ArtifactMissingError(f"Required artifact is missing: {relative_path}") from None

    # -- context-based API (target interface) ------------------------------

    def thresholds(self, context: StageJobContext) -> pl.DataFrame:
        return self.threshold_frame(self._resolve(context, "thresholds"))

    def calibration_scores(self, context: StageJobContext) -> pl.DataFrame:
        return self.calibration_score_frame(self._resolve(context, "calibration_scores"))

    def test_scores(self, context: StageJobContext) -> pl.DataFrame:
        return self.test_score_frame(self._resolve(context, "test_scores"))

    def client_metrics(self, context: StageJobContext) -> pl.DataFrame:
        return self.client_metric_frame(self._resolve(context, "client_metrics"))

    def thresholds_and_calibration(
        self, threshold_context: StageJobContext, score_context: StageJobContext
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        return (
            self.thresholds(threshold_context),
            self.calibration_scores(score_context),
        )

    def checkpoint_bytes(self, context: StageJobContext) -> bytes:
        return self.read_bytes(self._resolve(context, "checkpoint"))

    def checkpoint_selection_bytes(self, context: StageJobContext) -> bytes:
        return self.read_bytes(self._resolve(context, "checkpoint_selection"))

    # -- internals ---------------------------------------------------------

    def _resolve(self, context: StageJobContext, output_name: str) -> str:
        if self._path_index is None:
            raise ArtifactMissingError(
                f"Cannot resolve '{output_name}' for context — no path index configured"
            )
        return self._path_index.resolve(
            producer_stage=StageKind.THRESHOLD_CONSTRUCTION if output_name == "thresholds"
            else StageKind.SCORE_GENERATION if output_name in ("calibration_scores", "test_scores")
            else StageKind.OPERATING_POINT_EVALUATION if output_name == "client_metrics"
            else StageKind.MODEL_TRAINING if output_name == "checkpoint"
            else StageKind.CHECKPOINT_SELECTION if output_name == "checkpoint_selection"
            else StageKind.OPERATING_POINT_EVALUATION,
            output_name=output_name,
            context=context,
        )

    def _read_validated(self, relative_path: str, validator, artifact_kind: str) -> pl.DataFrame:
        try:
            raw = self._store.read_bytes(relative_path)
        except ArtifactFileMissingError:
            raise ArtifactMissingError(f"Required {artifact_kind} artifact is missing: {relative_path}") from None
        try:
            frame = pl.read_parquet(BytesIO(raw))
        except Exception as exc:
            raise ArtifactSchemaViolationError(
                f"Cannot parse {artifact_kind} artifact at {relative_path}: {exc}"
            ) from exc
        try:
            return validator(frame)
        except Exception as exc:
            raise ArtifactSchemaViolationError(
                f"{artifact_kind.capitalize()} artifact at {relative_path} failed schema validation: {exc}"
            ) from exc
