"""Resolved protocol-level record types shared across configuration, analysis, and reporting.

These records are pure-data attrs classes that live in the pipeline package (the bottom layer)
so every package can import them without creating circular or transitive import violations.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import cast

from attrs import define, field

from datp_core.pipeline.identifiers import StatisticalProfileId
from datp_core.pipeline.values import PositiveInt, Probability


class BootstrapMethod(StrEnum):
    BCA_BOOTSTRAP = "bca_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"


@define(frozen=True, slots=True, kw_only=True)
class StatisticalProfileRecord:
    """Resolved, executable statistical analysis contract (BCa/percentile bootstrap, Wilcoxon, etc.)."""

    identifier: StatisticalProfileId
    method: str | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


@define(frozen=True, slots=True, kw_only=True)
class FieldEncodingRecord:
    bytes_per_field: int
    byte_order: str


@define(frozen=True, slots=True, kw_only=True)
class ThresholdExchangeEntryRecord:
    uplink_fields_per_client: tuple[str, ...] | None
    downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_uplink_fields_per_client_per_candidate: tuple[str, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class ThresholdExchangeRecord:
    direction: str
    b1: ThresholdExchangeEntryRecord
    b2: ThresholdExchangeEntryRecord
    b4: ThresholdExchangeEntryRecord
    federated_summary: ThresholdExchangeEntryRecord


@define(frozen=True, slots=True, kw_only=True)
class ModelExchangeRecord:
    field_width: str
    directions: tuple[str, ...]
    bytes_per_round_formula: str


@define(frozen=True, slots=True, kw_only=True)
class CheckpointStorageRecord:
    contents: tuple[str, ...]
    model_parameter_bytes_formula: str


@define(frozen=True, slots=True, kw_only=True)
class CommunicationEstimationContractRecord:
    estimate_basis: str
    field_encodings: Mapping[str, FieldEncodingRecord]
    threshold_exchange: ThresholdExchangeRecord
    candidate_grid_payload: str
    model_exchange: ModelExchangeRecord
    checkpoint_storage: CheckpointStorageRecord
    filename_match_is_not_lineage_evidence: bool
    frozen_artifacts_immutable: bool
    ambiguous_latest_reference: str


@define(frozen=True, slots=True, kw_only=True)
class BenignDecisionRateRecord:
    configured: bool
    value: float | None
    required_fields: tuple[str, ...]
    finite_value_validation: str
    non_negative_validation: str
    unavailable_behavior: str
    invented_rate_forbidden: bool


@define(frozen=True, slots=True, kw_only=True)
class OperationalInputsRecord:
    benign_decision_rate: BenignDecisionRateRecord


@define(frozen=True, slots=True, kw_only=True)
class NestedReplicatePolicyRecord:
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


@define(frozen=True, slots=True, kw_only=True)
class ResultTypeRecord:
    identifier: str
    permitted_evidence_roles: tuple[str, ...]


# --- Reporting types ---


@define(frozen=True, slots=True, kw_only=True)
class ReportColumnRecord:
    name: str
    unit: str
    direction: str


def _as_optional_report_columns(value: object) -> tuple[ReportColumnRecord, ...] | None:
    if value is None:
        return None
    return cast("tuple[ReportColumnRecord, ...]", tuple(cast("list[ReportColumnRecord]", value)))


@define(frozen=True, slots=True, kw_only=True)
class ReportProfileRecord:
    identifier: str
    artifact_type: str
    table_type: str | None
    figure_type: str | None
    estimate_basis: str | None
    columns: tuple[ReportColumnRecord, ...] | None = field(converter=_as_optional_report_columns)
    series: tuple[ReportColumnRecord, ...] | None = field(converter=_as_optional_report_columns)


@define(frozen=True, slots=True, kw_only=True)
class ReportDefaultsRecord:
    ordering: str
    missing_value_policy: str
    table_output_formats: tuple[str, ...]
    figure_output_formats: tuple[str, ...]
    provenance_required_per_artifact: bool
    analysis_defined_direction_token: str
