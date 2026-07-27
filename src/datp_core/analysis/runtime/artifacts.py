"""Typed analysis artifact repository.

Analysis capabilities request domain artifacts, not bytes or arbitrary relative paths.
Schema validation occurs before returning any artifact.

Path resolution is handled by a private ``_ArtifactPathIndex`` that maps
``AnalysisInputCoordinates`` to relative paths.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from io import BytesIO
from typing import TypeVar

import polars as pl
from pydantic import BaseModel, ConfigDict, TypeAdapter
from safetensors.torch import load as load_safetensors

from datp_core.analysis.contracts import (
    AnalysisResult,
    CheckpointSelectionArtifact,
    DittoLossObservation,
    FederatedProximalLossObservation,
    PrerequisiteAnalysisReference,
)
from datp_core.analysis.enums import ArtifactKind
from datp_core.analysis.errors import ArtifactMissingError, ArtifactSchemaViolationError
from datp_core.artifacts.errors import ArtifactFileMissingError
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame, validate_test_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.context import AnalysisContext, DataContext, EvaluationContext, TrainingContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput

T = TypeVar("T", bound=AnalysisResult)

_adapter = TypeAdapter(tuple[AnalysisResult, ...])


class AnalysisArtifactReference(BaseModel):
    """Typed reference mapping declared input coordinates to relative storage path."""

    model_config = ConfigDict(frozen=True)

    coordinates: AnalysisInputCoordinates
    relative_path: str


class _ArtifactPathIndex:
    """Immutable exact-coordinate index over declared stage inputs."""

    def __init__(self, references: tuple[AnalysisArtifactReference, ...]) -> None:
        by_coordinates: dict[AnalysisInputCoordinates, str] = {ref.coordinates: ref.relative_path for ref in references}
        if len(by_coordinates) != len(references):
            raise ArtifactSchemaViolationError("Statistical analysis has duplicate artifact coordinates")
        self._paths: dict[AnalysisInputCoordinates, str] = by_coordinates

    @classmethod
    def from_stage_inputs(cls, inputs: tuple[StageInput, ...]) -> _ArtifactPathIndex:
        artifact_refs: list[AnalysisArtifactReference] = []
        for item in inputs:
            if item.coordinates is None:
                raise ArtifactMissingError(f"Analysis input '{item.name}' lacks typed coordinates")
            artifact_refs.append(
                AnalysisArtifactReference(coordinates=item.coordinates, relative_path=item.relative_path)
            )
        return cls(tuple(artifact_refs))

    def resolve(
        self,
        *,
        producer_stage: StageKind,
        output_name: str,
        context: DataContext | TrainingContext | EvaluationContext | AnalysisContext,
    ) -> str:
        coordinates = AnalysisInputCoordinates(
            producer_stage=producer_stage,
            output_name=output_name,
            context=context,
        )
        try:
            return self._paths[coordinates]
        except KeyError:
            raise ArtifactMissingError(
                f"Analysis input not declared: stage={producer_stage.value}, output={output_name}, context={context}"
            ) from None


class AnalysisArtifactRepository:
    """Typed access to validated analysis artifacts backed by an ArtifactStore."""

    def __init__(self, store: ArtifactStore, path_index: _ArtifactPathIndex | None = None) -> None:
        self._store = store
        self._path_index = path_index

    def thresholds(self, context: EvaluationContext) -> pl.DataFrame:
        """Load and validate the threshold frame for *context*."""
        path = self._resolve(context, ArtifactKind.THRESHOLD, StageKind.THRESHOLD_CONSTRUCTION, "thresholds")
        return self._read_validated_frame(path, validate_threshold_frame, "threshold")

    def calibration_scores(self, context: TrainingContext | EvaluationContext) -> pl.DataFrame:
        """Load and validate the calibration scores frame for *context*."""
        path = self._resolve(context, ArtifactKind.CALIBRATION_SCORE, StageKind.SCORE_GENERATION, "calibration_scores")
        return self._read_validated_frame(path, validate_calibration_score_frame, "calibration score")

    def test_scores(self, context: TrainingContext | EvaluationContext) -> pl.DataFrame:
        """Load and validate the test scores frame for *context*."""
        path = self._resolve(context, ArtifactKind.TEST_SCORE, StageKind.SCORE_GENERATION, "test_scores")
        return self._read_validated_frame(path, validate_test_score_frame, "test score")

    def client_metrics(self, context: EvaluationContext) -> pl.DataFrame:
        """Load and validate the client metrics frame for *context*."""
        path = self._resolve(
            context, ArtifactKind.CLIENT_METRIC, StageKind.OPERATING_POINT_EVALUATION, "client_metrics"
        )
        return self._read_validated_frame(path, validate_client_metric_frame, "client metric")

    def checkpoint_parameter_count(self, context: TrainingContext | EvaluationContext) -> int:
        """Inspect the model checkpoint safetensors artifact and return total parameter count."""
        path = self._resolve(context, ArtifactKind.CHECKPOINT, StageKind.MODEL_TRAINING, "checkpoint")
        data = self._read_bytes(path)
        try:
            tensors = load_safetensors(data)
            return sum(tensor.numel() for tensor in tensors.values())
        except (TypeError, ValueError, RuntimeError) as exc:
            raise ArtifactSchemaViolationError(f"Cannot parse checkpoint safetensors at {path}: {exc}") from exc

    def checkpoint_selection(self, context: DataContext) -> CheckpointSelectionArtifact:
        """Load and parse checkpoint selection JSON artifact into typed record."""
        path = self._resolve(
            context, ArtifactKind.CHECKPOINT_SELECTION, StageKind.CHECKPOINT_SELECTION, "checkpoint_selection"
        )
        data = self._read_bytes(path)
        try:
            parsed = json.loads(data.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ArtifactSchemaViolationError("Checkpoint selection payload must be a JSON dictionary")

            # Transform storage format (dict-based losses) to model format (tuple of observations)
            fedprox_losses_raw = parsed.pop("mean_benign_calibration_loss_by_mu", None)
            ditto_losses_raw = parsed.pop("mean_benign_calibration_loss_by_weight", None)

            if isinstance(fedprox_losses_raw, dict):
                parsed["federated_proximal_losses"] = [
                    FederatedProximalLossObservation(proximal_mu=float(k), mean_benign_calibration_loss=float(v))
                    for k, v in fedprox_losses_raw.items()
                ]

            if isinstance(ditto_losses_raw, dict):
                parsed["ditto_losses"] = [
                    DittoLossObservation(proximal_weight=float(k), mean_benign_calibration_loss=float(v))
                    for k, v in ditto_losses_raw.items()
                ]

            return CheckpointSelectionArtifact.model_validate(parsed)

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ArtifactSchemaViolationError(f"Cannot parse checkpoint selection JSON at {path}: {exc}") from exc

    def prerequisite_result(
        self,
        reference: PrerequisiteAnalysisReference,
        expected_type: type[T],
    ) -> T:
        """Load and decode a prerequisite analysis result of expected_type matching reference."""
        ctx = AnalysisContext(experiment_id=reference.experiment_id)
        path = (
            self._path_index.resolve(
                producer_stage=StageKind.RESULT_FREEZE, output_name="statistical_result", context=ctx
            )
            if self._path_index is not None
            else ""
        )

        if not path:
            raise ArtifactMissingError(f"Prerequisite result '{reference.analysis_label.value}' is unavailable")

        data = self._read_bytes(path)

        try:
            results = _adapter.validate_json(data)
        except (TypeError, ValueError) as exc:
            raise ArtifactSchemaViolationError(
                f"Prerequisite frozen artifact at {path} failed Pydantic validation: {exc}"
            ) from exc

        for result in results:
            if isinstance(result, expected_type) and result.analysis_label == reference.analysis_label:
                return result

        type_name = expected_type.__name__
        raise ArtifactMissingError(
            f"Prerequisite result '{reference.analysis_label.value}' of type '{type_name}' not found"
        )

    # -- Internal helpers --------------------------------------------------

    def _resolve(
        self,
        context: DataContext | TrainingContext | EvaluationContext | AnalysisContext,
        kind: ArtifactKind,
        producer_stage: StageKind,
        output_name: str,
    ) -> str:
        if self._path_index is None:
            raise ArtifactMissingError(f"Cannot resolve '{kind.value}' artifact — no path index configured")
        return self._path_index.resolve(producer_stage=producer_stage, output_name=output_name, context=context)

    def _read_bytes(self, relative_path: str) -> bytes:
        try:
            return self._store.read_bytes(relative_path)
        except ArtifactFileMissingError:
            raise ArtifactMissingError(f"Required artifact is missing at path: {relative_path}") from None

    def _read_validated_frame(
        self, relative_path: str, validator: Callable[[pl.DataFrame], pl.DataFrame], artifact_kind: str
    ) -> pl.DataFrame:
        raw = self._read_bytes(relative_path)
        try:
            frame = pl.read_parquet(BytesIO(raw))
        except (pl.exceptions.PolarsError, TypeError, ValueError) as exc:
            raise ArtifactSchemaViolationError(
                f"Cannot parse {artifact_kind} parquet artifact at {relative_path}: {exc}"
            ) from exc
        try:
            return validator(frame)
        except (TypeError, ValueError) as exc:
            raise ArtifactSchemaViolationError(
                f"{artifact_kind.capitalize()} artifact at {relative_path} failed schema validation: {exc}"
            ) from exc
