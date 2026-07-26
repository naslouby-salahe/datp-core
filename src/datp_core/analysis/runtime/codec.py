"""Canonical typed codec for analysis results using cattrs.

This is the ONLY cattrs ``Converter`` in the analysis package. All result
structure / unstructure hooks are registered here. Capability code must never
create secondary converters or call ``attrs.asdict`` / ``astuple`` directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from attrs import asdict
from cattrs import Converter

from datp_core.analysis.contracts import ConfidenceInterval
from datp_core.core.identifiers import ExperimentId, MetricId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed

if TYPE_CHECKING:
    from datp_core.analysis.contracts import PairedThresholdAnalysisResult

T = TypeVar("T")

_converter = Converter()


# ---------------------------------------------------------------------------
# Value-object hooks
# ---------------------------------------------------------------------------


def _configure_defaults() -> None:
    _converter.register_structure_hook(Seed, lambda v, _: Seed(int(v)))
    _converter.register_unstructure_hook(Seed, lambda s: s.value)
    _converter.register_structure_hook(ExperimentId, lambda v, _: ExperimentId(str(v)))
    _converter.register_unstructure_hook(ExperimentId, lambda e: e.value)
    _converter.register_structure_hook(MetricId, lambda v, _: MetricId(str(v)))
    _converter.register_unstructure_hook(MetricId, lambda m: m.value)
    _converter.register_structure_hook(ThresholdPolicyId, lambda v, _: ThresholdPolicyId(str(v)))
    _converter.register_unstructure_hook(ThresholdPolicyId, lambda p: p.value)
    _converter.register_structure_hook(Probability, lambda v, _: Probability(float(v)))
    _converter.register_unstructure_hook(Probability, lambda p: p.value)
    _converter.register_structure_hook(
        ConfidenceInterval,
        lambda v, _: ConfidenceInterval(
            lower_bound=float(v["lower_bound"]),
            upper_bound=float(v["upper_bound"]),
            confidence_level=Probability(float(v["confidence_level"])),
            method=str(v["method"]),
        ),
    )


_configure_defaults()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def structure_analysis_result(payload: dict[str, object], target_type: type[T]) -> T:
    """Structure a plain dict into the given attrs class."""
    return _converter.structure(payload, target_type)


def unstructure_analysis_result(instance: object) -> dict[str, object]:
    """Unstructure an attrs instance into a JSON-safe dict."""
    return asdict(instance, recurse=True)


def structure_paired_result(payload: dict[str, object]) -> PairedThresholdAnalysisResult:
    """Structure a prerequisite paired-result payload."""
    from datp_core.analysis.contracts import PairedThresholdAnalysisResult

    return _converter.structure(payload, PairedThresholdAnalysisResult)
