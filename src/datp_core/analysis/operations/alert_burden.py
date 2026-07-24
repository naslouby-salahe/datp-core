"""Alert-burden analysis: the per-client alert-burden estimate (currently always unconfigured)."""

from __future__ import annotations

from datp_core.analysis.operations.models import AlertBurdenAnalysisResult
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.experiments.models import AlertBurdenAnalysisRecord


def analyze_alert_burden(
    analysis: AlertBurdenAnalysisRecord, *, config: ResolvedProjectConfiguration
) -> AlertBurdenAnalysisResult:
    rate = config.operational_inputs.benign_decision_rate
    if not rate.configured or rate.value is None:
        return AlertBurdenAnalysisResult(
            analysis_label=analysis.label,
            formula=analysis.formula,
            status=analysis.unavailable_behavior,
            reason=f"required operational input '{analysis.required_operational_input}' is not configured",
        )
    raise ValueError("Configured operational alert-burden rates require executable source provenance")


__all__ = ["analyze_alert_burden"]
