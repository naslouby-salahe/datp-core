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

from pydantic import BaseModel, ConfigDict


class FieldEncodingRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    bytes_per_field: int
    byte_order: str


class ThresholdExchangeEntryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    uplink_fields_per_client: tuple[str, ...] | None
    downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_uplink_fields_per_client_per_candidate: tuple[str, ...] | None


class ThresholdExchangeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    direction: str
    b1: ThresholdExchangeEntryRecord
    b2: ThresholdExchangeEntryRecord
    b4: ThresholdExchangeEntryRecord
    federated_summary: ThresholdExchangeEntryRecord


class ModelExchangeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    field_width: str
    directions: tuple[str, ...]
    bytes_per_round_formula: str


class CheckpointStorageRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    contents: tuple[str, ...]
    model_parameter_bytes_formula: str


class CommunicationEstimationContractRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    estimate_basis: str
    field_encodings: Mapping[str, FieldEncodingRecord]
    threshold_exchange: ThresholdExchangeRecord
    candidate_grid_payload: str
    model_exchange: ModelExchangeRecord
    checkpoint_storage: CheckpointStorageRecord


class BenignDecisionRateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    configured: bool
    value: float | None
    required_fields: tuple[str, ...]
    finite_value_validation: str
    non_negative_validation: str
    unavailable_behavior: str
    invented_rate_forbidden: bool


class OperationalInputsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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
