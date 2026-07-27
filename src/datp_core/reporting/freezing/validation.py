"""Result freeze validation: analysis labels, seed completeness, metric statuses, provenance."""

from __future__ import annotations

import json
from collections.abc import Sequence

from datp_core.evaluation.enums import MetricStatus
from datp_core.experiments import ExperimentRecord
from datp_core.reporting.freezing.errors import ResultFreezeError


def _decode_result_list(payload: bytes) -> list[dict[str, object]]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ResultFreezeError("Statistical summary is not valid JSON") from exc
    if not isinstance(decoded, list):
        raise ResultFreezeError("Statistical summary must be a JSON list")
    results: list[dict[str, object]] = []
    for index, value in enumerate(decoded):
        if not isinstance(value, dict):
            raise ResultFreezeError(f"Statistical result {index} must be a JSON object")
        label = value.get("analysis_label")
        if not isinstance(label, str) or not label:
            raise ResultFreezeError(f"Statistical result {index} lacks a non-empty analysis_label")
        results.append(value)
    return results


def validate_analysis_labels(experiment: ExperimentRecord, results: list[dict[str, object]]) -> None:
    expected_labels = {analysis.label for analysis in experiment.analyses}
    actual_labels = {record["analysis_label"] for record in results}
    missing_labels = sorted(expected_labels - actual_labels)
    if missing_labels:
        raise ResultFreezeError(f"Result freeze is missing configured analyses: {', '.join(missing_labels)}")


def validate_source_files(source_files: Sequence[tuple[str, str]]) -> None:
    if not source_files:
        raise ResultFreezeError("Result freeze requires the statistical summary artifact")
    if source_files[0][1] != "statistical_result":
        raise ResultFreezeError("Result freeze requires the statistical summary as its first input")


def validate_seed_completeness(results: list[dict[str, object]], seed_count: int) -> set[int]:
    seeds_present: set[int] = set()
    for record in results:
        seed_val = record.get("seed")
        if isinstance(seed_val, int):
            seeds_present.add(seed_val)
        elif isinstance(seed_val, (int, float)) and not isinstance(seed_val, bool):
            seeds_present.add(int(seed_val))
        for key in ("seeds", "training_seeds"):
            seeds = record.get(key)
            if isinstance(seeds, list):
                for s in seeds:
                    if isinstance(s, int):
                        seeds_present.add(s)
    if len(seeds_present) < seed_count:
        raise ResultFreezeError(
            f"Result freeze requires {seed_count} seeds; only {len(seeds_present)} distinct seeds found"
        )
    return seeds_present


_RESOLVED_STATUS_VALUES = frozenset(status.value for status in MetricStatus)


def validate_metric_statuses(results: list[dict[str, object]]) -> None:
    unresolved_statuses: list[str] = []
    for record in results:
        for key, value in record.items():
            if isinstance(key, str) and key.endswith("_status") and isinstance(value, str):
                if value not in _RESOLVED_STATUS_VALUES:
                    unresolved_statuses.append(f"{record.get('analysis_label', '?')}:{key}={value}")
    if unresolved_statuses:
        raise ResultFreezeError(
            f"Result freeze requires all metric statuses to be resolved; "
            f"found {len(unresolved_statuses)} unresolved: {', '.join(unresolved_statuses[:5])}"
        )
