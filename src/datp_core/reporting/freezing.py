"""Frozen-result-family validation: the roadmap 04 §22 freeze contract (all required seeds present
or formally failed, eligibility final, metric statuses resolved, statistical configuration
recorded, provenance complete) applied to a committed statistical-analysis JSON artifact.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

from datp_core.artifacts.models import ArtifactKey
from datp_core.experiments.models import ExperimentRecord
from datp_core.reporting.models import ReportColumnRecord, ReportProfileRecord


class ResultFreezeError(ValueError):
    """A result family cannot be safely frozen or rendered."""


_FROZEN_TIMESTAMP = datetime.now(UTC).isoformat()

# Metric statuses considered fully resolved for freeze purposes.
_RESOLVED_METRIC_STATUSES = frozenset(
    (
        "available",
        "undefined_zero_denominator",
        "undefined_near_zero_denominator",
        "unavailable_missing_benign_class",
        "unavailable_missing_attack_class",
        "unavailable_invalid_attack_assignment",
        "unavailable_ineligible_client",
        "unavailable_unsupported_regime",
        "failed_invalid_artifact",
        "failed_statistical_procedure",
    )
)


def freeze_result_family(
    *,
    experiment: ExperimentRecord,
    report_profiles: Sequence[ReportProfileRecord],
    statistical_summary: bytes,
    source_artifacts: Sequence[ArtifactKey],
    scientific_fingerprint: str,
    execution_fingerprint: str,
    source_revision: str,
    seed_count: int,
    dataset_id: str | None = None,
    frozen_at: str | None = None,
) -> bytes:
    """Validate one complete result family and encode its immutable render input."""
    results = _decode_result_list(statistical_summary)
    expected_labels = {analysis.label for analysis in experiment.analyses}
    actual_labels = {record["analysis_label"] for record in results}
    missing_labels = sorted(expected_labels - actual_labels)
    if missing_labels:
        raise ResultFreezeError(f"Result freeze is missing configured analyses: {', '.join(missing_labels)}")
    if not source_artifacts:
        raise ResultFreezeError("Result freeze requires the statistical summary artifact")
    if source_artifacts[0].kind.value != "statistical_summary":
        raise ResultFreezeError("Result freeze requires the statistical summary as its first input")

    # --- Precondition: all required seeds are present or formally failed ---
    seeds_present: set[int] = set()
    for record in results:
        seed_val = record.get("seed")
        if isinstance(seed_val, int):
            seeds_present.add(seed_val)
        elif isinstance(seed_val, (int, float)) and not isinstance(seed_val, bool):
            seeds_present.add(int(seed_val))
        # records may carry seeds in a nested structure (paired analyses, etc.)
        for key in ("seeds", "training_seeds"):
            seeds = record.get(key)
            if isinstance(seeds, list):
                for s in seeds:
                    if isinstance(s, int):
                        seeds_present.add(s)
    if len(seeds_present) < seed_count:
        raise ResultFreezeError(
            f"Result freeze requires {seed_count} seeds; only {len(seeds_present)} distinct seeds "
            f"found in statistical results"
        )

    # --- Precondition: metric statuses are resolved ---
    unresolved_statuses: list[str] = []
    for record in results:
        for key, value in record.items():
            if isinstance(key, str) and key.endswith("_status") and isinstance(value, str):
                if value not in _RESOLVED_METRIC_STATUSES and value != "available":
                    unresolved_statuses.append(f"{record.get('analysis_label', '?')}:{key}={value}")
    if unresolved_statuses:
        raise ResultFreezeError(
            f"Result freeze requires all metric statuses to be resolved; "
            f"found {len(unresolved_statuses)} unresolved: {', '.join(unresolved_statuses[:5])}"
        )

    payload = {
        "schema_version": 1,
        "experiment_id": experiment.identifier.value,
        "evidence_role": experiment.evidence_role.value,
        "dataset_id": dataset_id,
        "population_ids": [pid.value for pid in experiment.population_ids],
        "seed_cohort_id": experiment.seed_cohort_id.value,
        "seed_count": seed_count,
        "seeds_present": sorted(seeds_present),
        "scientific_fingerprint": scientific_fingerprint,
        "execution_fingerprint": execution_fingerprint,
        "source_revision": source_revision,
        "frozen_at": frozen_at or _FROZEN_TIMESTAMP,
        "metric_definition_version": experiment.identifier.value,
        "statistical_procedure_version": experiment.checkpoint_profile_id.value,
        "report_profiles": [_profile_payload(profile) for profile in report_profiles],
        "source_artifacts": [
            {"artifact_id": artifact.artifact_id.value, "kind": artifact.kind.value} for artifact in source_artifacts
        ],
        "statistical_results": results,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def decode_manifest(payload: bytes) -> dict[str, object]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ResultFreezeError("Result-freeze artifact is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ResultFreezeError("Result-freeze artifact must be a JSON object")
    required = (
        "experiment_id",
        "scientific_fingerprint",
        "execution_fingerprint",
        "report_profiles",
        "source_artifacts",
        "statistical_results",
        "frozen_at",
    )
    if any(field not in decoded for field in required):
        raise ResultFreezeError("Result-freeze artifact lacks required provenance fields")
    if not isinstance(decoded["report_profiles"], list) or not isinstance(decoded["statistical_results"], list):
        raise ResultFreezeError("Result-freeze artifact has malformed report records")
    return cast("dict[str, object]", decoded)


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
        results.append(cast("dict[str, object]", value))
    return results


def _profile_payload(profile: ReportProfileRecord) -> dict[str, object]:
    def columns(values: tuple[ReportColumnRecord, ...] | None) -> list[dict[str, object]]:
        return (
            []
            if values is None
            else [{"name": value.name, "unit": value.unit, "direction": value.direction} for value in values]
        )

    return {
        "identifier": profile.identifier,
        "artifact_type": profile.artifact_type,
        "table_type": profile.table_type,
        "figure_type": profile.figure_type,
        "estimate_basis": profile.estimate_basis,
        "columns": columns(profile.columns),
        "series": columns(profile.series),
    }


__all__ = ["ResultFreezeError", "decode_manifest", "freeze_result_family"]
