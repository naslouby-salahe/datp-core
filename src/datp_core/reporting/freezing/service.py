"""Result family freezing service — validates and encodes immutable render input."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

from datp_core.config.report_profiles import ReportColumnRecord, ReportProfileRecord
from datp_core.experiments import ExperimentRecord
from datp_core.reporting.freezing.validation import (
    _decode_result_list,
    validate_analysis_labels,
    validate_metric_statuses,
    validate_seed_completeness,
    validate_source_files,
)


def freeze_result_family(
    *,
    experiment: ExperimentRecord,
    report_profiles: Sequence[ReportProfileRecord],
    statistical_summary: bytes,
    source_files: Sequence[tuple[str, str]],
    scientific_fingerprint: str,
    execution_fingerprint: str,
    source_revision: str,
    seed_count: int,
    dataset_id: str | None = None,
    frozen_at: str | None = None,
) -> bytes:
    """Validate one complete result family and encode its immutable render input."""
    results = _decode_result_list(statistical_summary)
    validate_analysis_labels(experiment, results)
    validate_source_files(source_files)
    seeds_present = validate_seed_completeness(results, seed_count)
    validate_metric_statuses(results)

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
        "frozen_at": frozen_at or datetime.now(UTC).isoformat(),
        "metric_definition_version": experiment.identifier.value,
        "statistical_procedure_version": experiment.checkpoint_profile_id.value,
        "report_profiles": [_profile_payload(profile) for profile in report_profiles],
        "source_files": [{"relative_path": path, "role": role} for path, role in source_files],
        "statistical_results": results,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8")


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


__all__ = ["freeze_result_family"]
