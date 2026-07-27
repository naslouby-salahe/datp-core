"""Mechanism-specific analysis contracts."""

from __future__ import annotations

from typing import Literal

from datp_core.analysis._base import FrozenModel
from datp_core.analysis.enums import (
    AlertBurdenStatus,
    AnalysisResultKind,
    ChronologyPolicy,
    CommunicationFieldIdentifier,
    NegativeRecoveryBehavior,
    ProducedField,
    ResourceEstimateBasis,
    TemporalOutcomeBand,
)
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel, MetricId
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import ClientScoreDistributionRecord, ThresholdTradeoffEntry


class ClientDistributionEntry(FrozenModel):
    client_id: ClientId
    distribution: ClientScoreDistributionRecord


class EvaluationDistributionResult(FrozenModel):
    evaluation_label: EvaluationLabel
    clients: tuple[ClientDistributionEntry, ...]


class DistributionMechanismSeedResult(FrozenModel):
    seed: Seed
    evaluations: tuple[EvaluationDistributionResult, ...]


class DistributionMechanismRawResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.DISTRIBUTION_MECHANISM] = AnalysisResultKind.DISTRIBUTION_MECHANISM
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


class ClientTradeoffEntry(FrozenModel):
    client_id: ClientId
    tradeoff: ThresholdTradeoffEntry


class DistributionMechanismTradeoffSeedResult(FrozenModel):
    seed: Seed
    per_client_tradeoff: tuple[ClientTradeoffEntry, ...]


class FieldFormulaContract(FrozenModel):
    field: ProducedField
    formula: str


class DistributionMechanismTradeoffResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.DISTRIBUTION_TRADEOFF] = AnalysisResultKind.DISTRIBUTION_TRADEOFF
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    field_formulas: tuple[FieldFormulaContract, ...]
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[DistributionMechanismTradeoffSeedResult, ...]


DistributionMechanismAnalysisResult = DistributionMechanismRawResult | DistributionMechanismTradeoffResult


class LockedClientDistributionAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.LOCKED_CLIENT_DISTRIBUTION] = AnalysisResultKind.LOCKED_CLIENT_DISTRIBUTION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    locked_client_identifier: ClientId
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


class TemporalRecoveryAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.TEMPORAL_RECOVERY] = AnalysisResultKind.TEMPORAL_RECOVERY
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    metric: MetricId
    static_reference_cv: tuple[float, ...]
    frozen_future_cv: tuple[float, ...]
    recalibrated_future_cv: tuple[float, ...]
    drift_excess: tuple[float, ...]
    recovered_amount: tuple[float, ...]
    recovery_ratio: tuple[float | None, ...]
    meaningful_degradation: bool
    drift_confidence_interval: tuple[float, float]
    outcome_band: TemporalOutcomeBand
    defined_recovery_ratio_seed_count: int
    mean_defined_recovery_ratio: float | None
    negative_recovery_policy: NegativeRecoveryBehavior
    chronology_unverifiable_policy: ChronologyPolicy


class AlertBurdenAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.ALERT_BURDEN] = AnalysisResultKind.ALERT_BURDEN
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    formula: str
    status: AlertBurdenStatus
    reason: str
    alerts_per_client_per_day: float | None = None
    benign_decision_rate_source: str | None = None


class ResourceCostEvaluationResult(FrozenModel):
    evaluation: EvaluationLabel
    transmitted_field_list: tuple[CommunicationFieldIdentifier, ...]
    estimated_threshold_message_bytes: int
    estimated_model_exchange_bytes_per_round: int
    estimated_checkpoint_storage_bytes: int


class ResourceCostSeedResult(FrozenModel):
    seed: Seed
    evaluations: tuple[ResourceCostEvaluationResult, ...]


class ResourceCostAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.RESOURCE_COST] = AnalysisResultKind.RESOURCE_COST
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    estimate_basis: ResourceEstimateBasis
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[ResourceCostSeedResult, ...]
