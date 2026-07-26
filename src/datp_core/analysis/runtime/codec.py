"""Canonical typed codec for analysis results using cattrs.

This is the ONLY cattrs ``Converter`` in the analysis package. All result
structure / unstructure hooks are registered here. Capability code must never
create secondary converters or call ``attrs.asdict`` / ``astuple`` directly.
"""

from __future__ import annotations

import json

from attrs import define
from cattrs import Converter
from cattrs.errors import BaseValidationError

from datp_core.analysis.contracts import AnalysisResultContract
from datp_core.analysis.enums import AnalysisResultKind
from datp_core.analysis.errors import AnalysisError, ResultDecodingError, ResultEncodingError
from datp_core.analysis.runtime.registry import RESULT_REGISTRY
from datp_core.core.identifiers import (
    AnalysisLabel,
    ClientId,
    ClusterLabel,
    EvaluationLabel,
    ExperimentId,
    MetricId,
    PartitionConditionId,
    ThresholdPolicyId,
)
from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed

JsonScalar = str | int | float | bool | None
JsonDict = dict[str, object]


@define(frozen=True, slots=True, kw_only=True)
class EncodedAnalysisResult:
    """Typed envelope representing an unstructured analysis result."""

    result_kind: AnalysisResultKind
    payload_version: int
    data: JsonDict


_converter = Converter()


def _configure_hooks() -> None:
    _converter.register_unstructure_hook(Seed, lambda s: s.value)
    _converter.register_structure_hook(Seed, lambda v, _: Seed(int(v)))

    _converter.register_unstructure_hook(ClientId, lambda c: c.value)
    _converter.register_structure_hook(ClientId, lambda v, _: ClientId(str(v)))

    _converter.register_unstructure_hook(MetricId, lambda m: m.value)
    _converter.register_structure_hook(MetricId, lambda v, _: MetricId(str(v)))

    _converter.register_unstructure_hook(ThresholdPolicyId, lambda p: p.value)
    _converter.register_structure_hook(ThresholdPolicyId, lambda v, _: ThresholdPolicyId(str(v)))

    _converter.register_unstructure_hook(PartitionConditionId, lambda p: p.value)
    _converter.register_structure_hook(PartitionConditionId, lambda v, _: PartitionConditionId(str(v)))

    _converter.register_unstructure_hook(AnalysisLabel, lambda a: a.value)
    _converter.register_structure_hook(AnalysisLabel, lambda v, _: AnalysisLabel(str(v)))

    _converter.register_unstructure_hook(EvaluationLabel, lambda e: e.value)
    _converter.register_structure_hook(EvaluationLabel, lambda v, _: EvaluationLabel(str(v)))

    _converter.register_unstructure_hook(ClusterLabel, lambda c: c.value)
    _converter.register_structure_hook(ClusterLabel, lambda v, _: ClusterLabel(str(v)))

    _converter.register_unstructure_hook(ExperimentId, lambda e: e.value)
    _converter.register_structure_hook(ExperimentId, lambda v, _: ExperimentId(str(v)))

    _converter.register_unstructure_hook(Probability, lambda p: p.value)
    _converter.register_structure_hook(Probability, lambda v, _: Probability(float(v)))


_configure_hooks()


def encode_analysis_result(instance: AnalysisResultContract) -> EncodedAnalysisResult:
    """Encode an analysis result instance into an EncodedAnalysisResult envelope."""
    try:
        kind = RESULT_REGISTRY.kind_for(instance)
        entry = RESULT_REGISTRY.get(kind)
        unstructured_data: JsonDict = _converter.unstructure(instance)
        return EncodedAnalysisResult(
            result_kind=kind,
            payload_version=entry.payload_version,
            data=unstructured_data,
        )
    except AnalysisError:
        raise
    except (BaseValidationError, TypeError, ValueError) as exc:
        raise ResultEncodingError(f"Failed to encode analysis result '{type(instance).__name__}': {exc}") from exc


def decode_analysis_result(envelope: EncodedAnalysisResult) -> AnalysisResultContract:
    """Decode an EncodedAnalysisResult envelope into an analysis result instance."""
    if not isinstance(envelope, EncodedAnalysisResult):
        raise ResultDecodingError(f"Result envelope must be EncodedAnalysisResult, got {type(envelope).__name__}")

    entry = RESULT_REGISTRY.get(envelope.result_kind)
    if envelope.payload_version != entry.payload_version:
        raise ResultDecodingError(
            f"Unsupported payload version {envelope.payload_version} for kind '{envelope.result_kind.value}' "
            f"(expected {entry.payload_version})"
        )

    try:
        return _converter.structure(envelope.data, entry.result_type)
    except AnalysisError:
        raise
    except (BaseValidationError, TypeError, ValueError, KeyError) as exc:
        raise ResultDecodingError(
            f"Failed to decode payload for result kind '{envelope.result_kind.value}': {exc}"
        ) from exc


def encode_result_json(instance: AnalysisResultContract) -> str:
    """Encode an analysis result instance into a JSON text string."""
    envelope = encode_analysis_result(instance)
    dict_envelope = {
        "result_kind": envelope.result_kind.value,
        "payload_version": envelope.payload_version,
        "data": envelope.data,
    }
    try:
        return json.dumps(dict_envelope, separators=(",", ":"), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ResultEncodingError(f"JSON serialization failed for result '{type(instance).__name__}': {exc}") from exc


def decode_result_json(json_str: str) -> AnalysisResultContract:
    """Decode a JSON text string into an analysis result instance."""
    try:
        raw = json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ResultDecodingError(f"Failed to parse JSON payload: {exc}") from exc

    if not isinstance(raw, dict):
        raise ResultDecodingError("JSON payload must be an object")

    raw_kind = raw.get("result_kind")
    payload_version = raw.get("payload_version")
    data = raw.get("data")
    if not isinstance(raw_kind, str) or not isinstance(payload_version, int) or not isinstance(data, dict):
        raise ResultDecodingError("Malformed JSON result envelope structure")

    try:
        kind = AnalysisResultKind(raw_kind)
    except ValueError:
        raise ResultDecodingError(f"Unknown result kind in JSON envelope: '{raw_kind}'") from None

    envelope = EncodedAnalysisResult(
        result_kind=kind,
        payload_version=payload_version,
        data=data,
    )
    return decode_analysis_result(envelope)
