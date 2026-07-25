"""Result ordering, Holm correction, and direct statistical-result persistence."""

from __future__ import annotations

import json
from typing import cast

from attrs import evolve

from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.result import AnalysisResult, analysis_result_to_payload
from datp_core.analysis.statistics.multiplicity import holm_adjust_p_values
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.jobs import StageJob


def apply_holm_correction(results: list[AnalysisResult]) -> list[AnalysisResult]:
    """Apply the Holm-Bonferroni correction across every paired-threshold analysis' p-value."""
    candidates: list[tuple[int, float]] = [
        (index, result.p_value)
        for index, result in enumerate(results)
        if isinstance(result, PairedThresholdAnalysisResult) and result.p_value is not None
    ]
    if len(candidates) < 2:
        return results
    adjusted = holm_adjust_p_values(value for _, value in candidates)
    updated = list(results)
    for (index, _), adjusted_value in zip(candidates, adjusted, strict=True):
        updated[index] = evolve(
            cast(PairedThresholdAnalysisResult, updated[index]), holm_adjusted_p_value=adjusted_value
        )
    return updated


def persist_analysis_results(
    *,
    store: ArtifactStore,
    job: StageJob,
    results: list[AnalysisResult],
) -> None:
    payload = json.dumps(
        [analysis_result_to_payload(result) for result in apply_holm_correction(results)],
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    store.write_bytes_atomic(job.output_path("statistical_result"), payload)


__all__ = ["apply_holm_correction", "persist_analysis_results"]
