"""Result records for resource-cost, alert-burden, and operational contract records."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define, field

from datp_core.core.immutability import FrozenJson, as_frozen_json_mapping, deep_freeze


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostEvaluationResult:
    evaluation: str
    transmitted_field_list: tuple[str, ...]
    estimated_threshold_message_bytes: int
    estimated_model_exchange_bytes_per_round: int
    estimated_checkpoint_storage_bytes: int


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostSeedResult:
    seed: int
    evaluations: tuple[ResourceCostEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostAnalysisResult:
    analysis_label: str
    estimate_basis: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[ResourceCostSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class AlertBurdenAnalysisResult:
    analysis_label: str
    formula: str
    status: str
    reason: str
    alerts_per_client_per_day: float | None = None
    benign_decision_rate_source: str | None = None


# --- Operational contract records (moved from evaluation) ---


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


__all__ = [
    "AlertBurdenAnalysisResult",
    "BenignDecisionRateRecord",
    "CheckpointStorageRecord",
    "CommunicationEstimationContractRecord",
    "FieldEncodingRecord",
    "ModelExchangeRecord",
    "OperationalInputsRecord",
    "ResourceCostAnalysisResult",
    "ResourceCostEvaluationResult",
    "ResourceCostSeedResult",
    "ThresholdExchangeEntryRecord",
    "ThresholdExchangeRecord",
]
