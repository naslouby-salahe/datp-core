"""Exact, planner-declared inputs consumed by statistical analyses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.statistics.models import ConfidenceInterval
from datp_core.core.identifiers import ExperimentId
from datp_core.core.numbers import Probability
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput
from datp_core.reporting.freezing.models import FrozenResultManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisArtifactRef:
    """One direct upstream artifact with its complete producer coordinates."""

    coordinates: AnalysisInputCoordinates
    relative_path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PrerequisiteExperimentResult:
    """A validated, immutable frozen result supplied by a configured prerequisite."""

    experiment_id: ExperimentId
    frozen_result_path: str
    frozen_result_checksum: str
    scientific_fingerprint: str
    result: FrozenResultManifest

    def paired_result(self, analysis_label: str) -> PairedThresholdAnalysisResult:
        matches = tuple(
            item
            for item in self.result.statistical_results
            if isinstance(item, dict) and item.get("analysis_label") == analysis_label and "seed_differences" in item
        )
        if len(matches) != 1:
            raise ValueError(
                f"Prerequisite '{self.experiment_id.value}' has no unique paired result for analysis '{analysis_label}'"
            )
        return _paired_result_from_payload(matches[0])


class AnalysisInputBundle:
    """Immutable exact-coordinate index over the statistical job's declared inputs."""

    def __init__(self, artifacts: tuple[AnalysisArtifactRef, ...]) -> None:
        by_coordinates = {artifact.coordinates: artifact.relative_path for artifact in artifacts}
        if len(by_coordinates) != len(artifacts):
            raise ValueError("Statistical analysis has duplicate artifact coordinates")
        self._paths: Mapping[AnalysisInputCoordinates, str] = MappingProxyType(by_coordinates)

    @classmethod
    def from_stage_inputs(cls, inputs: tuple[StageInput, ...]) -> AnalysisInputBundle:
        artifacts: list[AnalysisArtifactRef] = []
        for item in inputs:
            if item.coordinates is None:
                raise ValueError(f"Analysis input '{item.name}' lacks typed coordinates")
            artifacts.append(AnalysisArtifactRef(coordinates=item.coordinates, relative_path=item.relative_path))
        return cls(tuple(artifacts))

    def require(self, *, producer_stage: StageKind, output_name: str, context: StageJobContext) -> str:
        coordinates = AnalysisInputCoordinates(
            producer_stage=producer_stage,
            output_name=output_name,
            context=context,
        )
        try:
            return self._paths[coordinates]
        except KeyError as exc:
            raise ValueError(
                f"Analysis input is not declared: stage={producer_stage.value}, output={output_name}, "
                f"context={context}"
            ) from exc

    def evaluation_metrics(self, context: StageJobContext) -> str:
        return self.require(
            producer_stage=StageKind.OPERATING_POINT_EVALUATION,
            output_name="client_metrics",
            context=context,
        )

    def thresholds(self, context: StageJobContext) -> str:
        return self.require(
            producer_stage=StageKind.THRESHOLD_CONSTRUCTION,
            output_name="thresholds",
            context=context,
        )

    def calibration_scores(self, context: StageJobContext) -> str:
        return self.require(
            producer_stage=StageKind.SCORE_GENERATION,
            output_name="calibration_scores",
            context=context,
        )

    def test_scores(self, context: StageJobContext) -> str:
        return self.require(
            producer_stage=StageKind.SCORE_GENERATION,
            output_name="test_scores",
            context=context,
        )

    def checkpoint(self, context: StageJobContext) -> str:
        return self.require(
            producer_stage=StageKind.MODEL_TRAINING,
            output_name="checkpoint",
            context=context,
        )

    def checkpoint_selection(self, context: StageJobContext) -> str:
        return self.require(
            producer_stage=StageKind.CHECKPOINT_SELECTION,
            output_name="checkpoint_selection",
            context=context,
        )


def _paired_result_from_payload(payload: dict[object, object]) -> PairedThresholdAnalysisResult:
    required = {
        "analysis_label",
        "metric",
        "first_threshold_policy",
        "second_threshold_policy",
        "training_seeds",
        "first_seed_values",
        "second_seed_values",
        "first_mean",
        "second_mean",
        "mean_difference",
        "confidence_interval",
        "p_value",
        "rank_biserial",
        "resample_count",
        "analysis_seed",
        "seed_differences",
        "sign_consistency",
        "zero_difference_count",
        "negative_difference_count",
    }
    if not required <= set(payload):
        raise ValueError("Prerequisite paired result is missing required fields")
    interval = payload["confidence_interval"]
    if (
        not isinstance(interval, dict)
        or not isinstance(interval.get("lower_bound"), (int, float))
        or not isinstance(interval.get("upper_bound"), (int, float))
        or not isinstance(interval.get("confidence_level"), (int, float))
        or not isinstance(interval.get("method"), str)
    ):
        raise ValueError("Prerequisite paired result has an invalid confidence interval")
    try:
        return PairedThresholdAnalysisResult(
            analysis_label=_string(payload, "analysis_label"),
            metric=_string(payload, "metric"),
            first_threshold_policy=_string(payload, "first_threshold_policy"),
            second_threshold_policy=_string(payload, "second_threshold_policy"),
            training_seeds=_int_tuple(payload, "training_seeds"),
            first_seed_values=_float_tuple(payload, "first_seed_values"),
            second_seed_values=_float_tuple(payload, "second_seed_values"),
            first_mean=_float(payload, "first_mean"),
            second_mean=_float(payload, "second_mean"),
            mean_difference=_float(payload, "mean_difference"),
            confidence_interval=ConfidenceInterval(
                lower_bound=float(interval["lower_bound"]),
                upper_bound=float(interval["upper_bound"]),
                confidence_level=Probability(float(interval["confidence_level"])),
                method=interval["method"],
            ),
            p_value=_optional_float(payload, "p_value"),
            rank_biserial=_optional_float(payload, "rank_biserial"),
            resample_count=_int(payload, "resample_count"),
            analysis_seed=_int(payload, "analysis_seed"),
            seed_differences=_float_tuple(payload, "seed_differences"),
            sign_consistency=_float(payload, "sign_consistency"),
            zero_difference_count=_int(payload, "zero_difference_count"),
            negative_difference_count=_int(payload, "negative_difference_count"),
            partition_condition=_optional_string(payload, "partition_condition"),
            federated_proximal_mu=_optional_float(payload, "federated_proximal_mu"),
            ditto_proximal_weight=_optional_float(payload, "ditto_proximal_weight"),
            threshold_quantile=_optional_float(payload, "threshold_quantile"),
            shrinkage_weight=_optional_float(payload, "shrinkage_weight"),
            calibration_sample_count=_optional_int(payload, "calibration_sample_count"),
            holm_adjusted_p_value=_optional_float(payload, "holm_adjusted_p_value"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Prerequisite paired result has invalid field types") from exc


def _string(payload: Mapping[object, object], name: str) -> str:
    value = payload[name]
    if not isinstance(value, str):
        raise ValueError(name)
    return value


def _optional_string(payload: Mapping[object, object], name: str) -> str | None:
    value = payload.get(name)
    if value is not None and not isinstance(value, str):
        raise ValueError(name)
    return value


def _float(payload: Mapping[object, object], name: str) -> float:
    value = payload[name]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(name)
    return float(value)


def _optional_float(payload: Mapping[object, object], name: str) -> float | None:
    value = payload.get(name)
    return None if value is None else _float(payload, name)


def _int(payload: Mapping[object, object], name: str) -> int:
    value = payload[name]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(name)
    return value


def _optional_int(payload: Mapping[object, object], name: str) -> int | None:
    value = payload.get(name)
    return None if value is None else _int(payload, name)


def _int_tuple(payload: Mapping[object, object], name: str) -> tuple[int, ...]:
    value = payload[name]
    if not isinstance(value, list):
        raise ValueError(name)
    return tuple(_int({name: item}, name) for item in value)


def _float_tuple(payload: Mapping[object, object], name: str) -> tuple[float, ...]:
    value = payload[name]
    if not isinstance(value, list):
        raise ValueError(name)
    return tuple(_float({name: item}, name) for item in value)


__all__ = ["AnalysisArtifactRef", "AnalysisInputBundle", "PrerequisiteExperimentResult"]
