"""Calibration-specific analysis contracts."""

from __future__ import annotations

from typing import Literal

from datp_core.analysis._base import FrozenModel
from datp_core.analysis.enums import (
    AnalysisResultKind,
    CoverageDirection,
    CoverageStatus,
    ProducedField,
    ReplicateAggregation,
)
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel
from datp_core.core.seeding import Seed


class ConformalClientCoverageRecord(FrozenModel):
    client_id: ClientId
    coverage: float | None
    absolute_coverage_error: float | None
    coverage_status: CoverageStatus
    finite_sample_rank: int
    calibration_count: int


class ConformalSeedCoverageResult(FrozenModel):
    seed: Seed
    per_client_coverage: tuple[ConformalClientCoverageRecord, ...]
    benign_true_negatives: int
    benign_total: int


class ConformalCoverageAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.CONFORMAL_COVERAGE] = AnalysisResultKind.CONFORMAL_COVERAGE
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    target_coverage: float
    achieved_marginal_coverage: float | None
    achieved_macro_client_coverage: float | None
    absolute_coverage_error: float | None
    coverage_direction: CoverageDirection | None
    seed_results: tuple[ConformalSeedCoverageResult, ...]


class QuantileEstimationClientResult(FrozenModel):
    client_id: ClientId
    absolute_threshold_error: float
    relative_threshold_error: float | None
    achieved_exceedance: float | None
    signed_attainment_error: float | None
    absolute_attainment_error: float | None


class QuantileEstimationEvaluationResult(FrozenModel):
    evaluation_label: EvaluationLabel
    per_client: tuple[QuantileEstimationClientResult, ...]
    within_term: float
    between_term: float
    between_ratio: float | None


class QuantileEstimationSeedResult(FrozenModel):
    seed: Seed
    oracle_threshold: float
    evaluations: tuple[QuantileEstimationEvaluationResult, ...]


class QuantileEstimationAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.QUANTILE_ESTIMATION] = AnalysisResultKind.QUANTILE_ESTIMATION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[QuantileEstimationSeedResult, ...]


class ThresholdStabilitySeedResult(FrozenModel):
    seed: Seed
    threshold_variance_across_replicates: float | None
    absolute_attainment_error: float | None
    worst_client_fpr: float | None
    clients_unavailable_at_size: tuple[ClientId, ...]


class ThresholdStabilityAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.THRESHOLD_STABILITY] = AnalysisResultKind.THRESHOLD_STABILITY
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    calibration_sample_count: int
    replicate_aggregation: ReplicateAggregation
    independent_inferential_unit: str
    seed_results: tuple[ThresholdStabilitySeedResult, ...]
