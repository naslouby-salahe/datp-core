"""Operational-cost and communication-estimation configuration schema: how the resource-cost and
alert-burden analyses' input contracts (field encodings, threshold/model exchange direction,
checkpoint storage, benign decision rate) are authored.

This is scientific *configuration* schema, not an analysis-execution feature, so it lives under
``datp_core.config`` rather than ``datp_core.analysis`` -- keeping it under ``analysis`` previously
made every data/learning/thresholding/evaluation handler that transitively imports
``ResolvedProjectConfiguration`` also transitively import the analysis package, violating this
repository's own layering contract (`importlinter.ini`'s
``data-thresholding-evaluation-do-not-import-downstream-features``). Kept as its own leaf module
(rather than merged into `config.models`) so both `config.models` and `config.resolution.protocols`
can depend on it without a circular import between them; `analysis.operations.resource_cost` (the
one analysis-side consumer) imports it from here, which is an ordinary analysis-depends-on-config
direction and does not reintroduce the violation.
"""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define


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
    "BenignDecisionRateRecord",
    "CheckpointStorageRecord",
    "CommunicationEstimationContractRecord",
    "FieldEncodingRecord",
    "ModelExchangeRecord",
    "OperationalInputsRecord",
    "ThresholdExchangeEntryRecord",
    "ThresholdExchangeRecord",
]
