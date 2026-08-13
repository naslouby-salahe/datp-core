from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import polars as pl
from pydantic import model_validator
from scipy.stats import spearmanr

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    ClientIdentityToken,
    DecisionRationale,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    ScoreFrameColumn,
    SplitProtocolId,
    TemporalState,
)
from datp_core.core.numeric import MetricValue, Ratio, Seed, SeedCount, SeedObservationCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import (
    ScoreArtifactManifest,
)
from datp_core.detector.scoring.models import FederatedScoreRecord
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL

type TemporalTrainingCoordinate = FederatedTrainingCoordinate | tuple[FederatedTrainingCoordinate, ...]


class TemporalProvenanceViolation(StrEnum):
    SCORE_EVIDENCE_CHANGED = "score_evidence_changed"


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY = "temporal_degradation_with_material_recovery"
    TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY = "temporal_degradation_with_partial_or_weak_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"
    BLOCKED_OR_UNAVAILABLE = "blocked_or_unavailable"


class TemporalSpearmanAvailability(StrEnum):
    AVAILABLE = "available"
    INSUFFICIENT_EVIDENCE_N_LT_5 = "insufficient_evidence_n_lt_5"
    UNDEFINED_ZERO_VARIATION = "undefined_zero_variation"


class TemporalSpearmanDiagnostic(StrictModel):
    availability: TemporalSpearmanAvailability
    valid_pair_count: SeedObservationCount
    value: MetricValue | None


class TemporalSeedProvenance(StrictModel):
    seed: Seed
    experiment: ExperimentId
    population: PopulationId
    threshold_method: FederatedThresholdMethod
    static_reference: TemporalDeploymentProvenance
    frozen_future: TemporalDeploymentProvenance
    recalibrated_future: TemporalDeploymentProvenance
    excluded_clients: tuple[ClientIdentity, ...] = ()
    unavailable_reasons: tuple[AnalysisReasonText, ...] = ()

    @model_validator(mode="after")
    def validate_bindings(self) -> TemporalSeedProvenance:
        if self.static_reference.state is not TemporalState.STATIC_REFERENCE:
            raise ValueError("static_reference provenance must use the static_reference state")
        if self.frozen_future.state is not TemporalState.FROZEN_FUTURE:
            raise ValueError("frozen_future provenance must use the frozen_future state")
        if self.recalibrated_future.state is not TemporalState.RECALIBRATED_FUTURE:
            raise ValueError("recalibrated_future provenance must use the recalibrated_future state")
        if self.static_reference.coordinate != self.frozen_future.coordinate:
            raise ValueError("static and frozen temporal states must share detector and preprocessing identity")
        if self.frozen_future.future_identity != self.recalibrated_future.future_identity:
            raise ValueError("frozen and recalibrated future must share detector, split, and evaluation scores")
        if any(client.population is not self.population for client in self.excluded_clients):
            raise ValueError("temporal exclusions must match the provenance population")
        if len(self.excluded_clients) != len(frozenset(self.excluded_clients)):
            raise ValueError("temporal excluded clients must be unique")
        return self


class TemporalClientTrajectory(StrictModel):
    seed: Seed
    client: ClientIdentity
    threshold_method: FederatedThresholdMethod
    eligible: bool
    exclusion_reason: AnalysisReasonText | None
    threshold_static: MetricValue | None
    threshold_frozen: MetricValue | None
    threshold_recalibrated: MetricValue | None
    fpr_static: MetricValue | None
    fpr_frozen: MetricValue | None
    fpr_recalibrated: MetricValue | None
    tpr_static: MetricValue | None = None
    tpr_frozen: MetricValue | None = None
    tpr_recalibrated: MetricValue | None = None
    balanced_accuracy_static: MetricValue | None = None
    balanced_accuracy_frozen: MetricValue | None = None
    balanced_accuracy_recalibrated: MetricValue | None = None
    macro_f1_static: MetricValue | None = None
    macro_f1_frozen: MetricValue | None = None
    macro_f1_recalibrated: MetricValue | None = None
    drift_js: MetricValue | None = None

    @model_validator(mode="after")
    def validate_eligibility(self) -> TemporalClientTrajectory:
        if self.eligible != (self.exclusion_reason is None):
            raise ValueError("temporal client eligibility and exclusion reason must agree")
        if self.eligible and any(
            value is None
            for value in (
                self.threshold_static,
                self.threshold_frozen,
                self.threshold_recalibrated,
                self.fpr_static,
                self.fpr_frozen,
                self.fpr_recalibrated,
            )
        ):
            raise ValueError("eligible temporal clients require all threshold and FPR observations")
        return self

    @property
    def client_id(self) -> ClientIdentityToken:
        return self.client.client_id

    @property
    def threshold_movement_frozen(self) -> MetricValue | None:
        if self.threshold_static is None or self.threshold_frozen is None:
            return None
        return MetricValue(self.threshold_frozen.value - self.threshold_static.value)

    @property
    def threshold_movement_recalibrated(self) -> MetricValue | None:
        if self.threshold_static is None or self.threshold_recalibrated is None:
            return None
        return MetricValue(self.threshold_recalibrated.value - self.threshold_static.value)

    @property
    def fpr_movement_frozen(self) -> MetricValue | None:
        if self.fpr_static is None or self.fpr_frozen is None:
            return None
        return MetricValue(self.fpr_frozen.value - self.fpr_static.value)

    @property
    def fpr_movement_recalibrated(self) -> MetricValue | None:
        if self.fpr_frozen is None or self.fpr_recalibrated is None:
            return None
        return MetricValue(self.fpr_recalibrated.value - self.fpr_frozen.value)

    @property
    def fpr_recovery(self) -> MetricValue | None:
        if self.fpr_frozen is None or self.fpr_recalibrated is None:
            return None
        return MetricValue(self.fpr_frozen.value - self.fpr_recalibrated.value)


TEMPORAL_DRIFT_JSD_BIN_COUNT = 64


def temporal_drift_js(
    historical_calibration: FederatedScoreRecord,
    future_recalibration: FederatedScoreRecord,
) -> MetricValue:
    if historical_calibration.scored_client != future_recalibration.scored_client:
        raise ScientificContractError(ErrorMessage("temporal drift JSD requires score records for one client"))
    historical = _score_values(historical_calibration)
    future = _score_values(future_recalibration)
    edges = np.unique(
        np.quantile(
            np.concatenate((historical, future)),
            np.linspace(0.0, 1.0, TEMPORAL_DRIFT_JSD_BIN_COUNT + 1, dtype=np.float64),
            method="linear",
        )
    )
    if len(edges) < 3:
        raise ScientificContractError(
            ErrorMessage("temporal drift JSD requires at least two nonzero-width pooled quantile bins")
        )
    historical_histogram, _ = np.histogram(historical, bins=edges)
    future_histogram, _ = np.histogram(future, bins=edges)
    left = historical_histogram.astype(np.float64)
    right = future_histogram.astype(np.float64)
    left /= left.sum()
    right /= right.sum()
    midpoint = (left + right) / 2.0
    divergence = 0.5 * (_kl_base2(left, midpoint) + _kl_base2(right, midpoint))
    return MetricValue(float(divergence))


def _kl_base2(probabilities: np.ndarray, reference: np.ndarray) -> float:
    positive = probabilities > 0.0
    return float(np.sum(probabilities[positive] * np.log2(probabilities[positive] / reference[positive])))


def temporal_drift_fpr_spearman(
    trajectories: tuple[TemporalClientTrajectory, ...],
) -> TemporalSpearmanDiagnostic:
    pairs = tuple(
        (trajectory.drift_js.value, trajectory.fpr_movement_frozen.value)
        for trajectory in trajectories
        if trajectory.eligible and trajectory.drift_js is not None and trajectory.fpr_movement_frozen is not None
    )
    count = SeedObservationCount(len(pairs))
    if count.value < 5:
        return TemporalSpearmanDiagnostic(
            availability=TemporalSpearmanAvailability.INSUFFICIENT_EVIDENCE_N_LT_5,
            valid_pair_count=count,
            value=None,
        )
    statistic = spearmanr(tuple(pair[0] for pair in pairs), tuple(pair[1] for pair in pairs)).statistic
    if not np.isfinite(statistic):
        return TemporalSpearmanDiagnostic(
            availability=TemporalSpearmanAvailability.UNDEFINED_ZERO_VARIATION,
            valid_pair_count=count,
            value=None,
        )
    return TemporalSpearmanDiagnostic(
        availability=TemporalSpearmanAvailability.AVAILABLE,
        valid_pair_count=count,
        value=MetricValue(float(statistic)),
    )


def _score_values(record: FederatedScoreRecord) -> np.ndarray:
    values = pl.scan_parquet(record.path).select(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).collect().to_series()
    array = values.to_numpy().astype(np.float64, copy=False)
    if array.size == 0 or not np.isfinite(array).all():
        raise ScientificContractError(ErrorMessage("temporal drift JSD requires finite non-empty score artifacts"))
    return array


class TemporalRecoveryResult(StrictModel):
    seed: Seed
    experiment: ExperimentId
    threshold_method: FederatedThresholdMethod
    static_reference_cv: MetricValue
    frozen_future_cv: MetricValue
    recalibrated_future_cv: MetricValue
    decision_protocol: TemporalDecisionProtocol
    provenance: TemporalSeedProvenance
    mean_fpr_static: MetricValue | None = None
    mean_fpr_frozen: MetricValue | None = None
    mean_fpr_recalibrated: MetricValue | None = None
    client_trajectories: tuple[TemporalClientTrajectory, ...] = ()
    drift_js_frozen_fpr_spearman: TemporalSpearmanDiagnostic | None = None
    unavailable_reason: AnalysisReasonText | None = None

    @model_validator(mode="after")
    def validate_recovery(self) -> TemporalRecoveryResult:
        if self.provenance.seed != self.seed:
            raise ValueError("temporal provenance seed must match the recovery seed")
        if (
            self.provenance.experiment is not self.experiment
            or self.provenance.threshold_method is not self.threshold_method
        ):
            raise ValueError("temporal provenance must match experiment and threshold method")
        trajectory_clients = tuple(item.client for item in self.client_trajectories)
        if len(trajectory_clients) != len(frozenset(trajectory_clients)):
            raise ValueError("temporal client trajectories must be unique by client")
        if any(item.seed != self.seed for item in self.client_trajectories):
            raise ValueError("temporal client trajectories must match the recovery seed")
        if any(item.threshold_method is not self.threshold_method for item in self.client_trajectories):
            raise ValueError("temporal client trajectories must match the recovery threshold method")
        if any(item.client.population is not self.provenance.population for item in self.client_trajectories):
            raise ValueError("temporal client trajectories must match the provenance population")
        return self

    @property
    def evidence_role(self) -> EvidenceRole:
        return EvidenceRole.TEMPORAL_BOUNDARY

    @property
    def drift_excess(self) -> MetricValue:
        return MetricValue(self.frozen_future_cv.value - self.static_reference_cv.value)

    @property
    def recovered_amount(self) -> MetricValue:
        return MetricValue(self.frozen_future_cv.value - self.recalibrated_future_cv.value)

    @property
    def _eligible_recovery_deltas(self) -> tuple[MetricValue, ...]:
        return tuple(
            MetricValue(item.fpr_frozen.value - item.fpr_recalibrated.value)
            for item in self.client_trajectories
            if item.eligible and item.fpr_frozen is not None and item.fpr_recalibrated is not None
        )

    @property
    def helped_fraction(self) -> Ratio | None:
        deltas = self._eligible_recovery_deltas
        return None if not deltas else Ratio(sum(item.value > 0.0 for item in deltas) / len(deltas))

    @property
    def harmed_fraction(self) -> Ratio | None:
        deltas = self._eligible_recovery_deltas
        return None if not deltas else Ratio(sum(item.value < 0.0 for item in deltas) / len(deltas))

    @property
    def unchanged_fraction(self) -> Ratio | None:
        deltas = self._eligible_recovery_deltas
        return None if not deltas else Ratio(sum(item.value == 0.0 for item in deltas) / len(deltas))

    @property
    def worst_client_fpr_recovery(self) -> MetricValue | None:
        eligible = tuple(
            item
            for item in self.client_trajectories
            if item.eligible and item.fpr_frozen is not None and item.fpr_recalibrated is not None
        )
        if not eligible:
            return None
        frozen = tuple(item.fpr_frozen for item in eligible)
        recalibrated = tuple(item.fpr_recalibrated for item in eligible)
        if any(item is None for item in frozen) or any(item is None for item in recalibrated):
            raise ScientificContractError(ErrorMessage("eligible temporal recovery requires available FPRs"))
        frozen_values = tuple(item.value for item in frozen if item is not None)
        recalibrated_values = tuple(item.value for item in recalibrated if item is not None)
        return MetricValue(max(frozen_values) - max(recalibrated_values))

    @property
    def drift_excess_materiality_threshold(self) -> MetricValue:
        return self.decision_protocol.drift_excess_materiality_threshold

    @property
    def material_recovery_ratio_minimum(self) -> Ratio:
        return self.decision_protocol.material_recovery_ratio_minimum

    @property
    def recovery_ratio(self) -> MetricValue | None:
        if self.unavailable_reason is not None:
            return None
        if self.drift_excess.value < self.drift_excess_materiality_threshold.value:
            return None
        return MetricValue(self.recovered_amount.value / self.drift_excess.value)

    @property
    def availability(self) -> AvailabilityStatus:
        if self.unavailable_reason is not None:
            return AvailabilityStatus.UNAVAILABLE
        return AvailabilityStatus.UNDEFINED if self.recovery_ratio is None else AvailabilityStatus.AVAILABLE

    @property
    def interpretation(self) -> TemporalInterpretation:
        if self.unavailable_reason is not None:
            return TemporalInterpretation.BLOCKED_OR_UNAVAILABLE
        if self.recovery_ratio is None:
            if self.drift_excess.value < 0.0:
                return TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
            return TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
        ratio = self.recovery_ratio.value
        if ratio >= self.material_recovery_ratio_minimum.value:
            return TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
        if self.recovered_amount.value > 0.0:
            return TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY
        return TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY

    @property
    def reason(self) -> AnalysisReasonText | None:
        if self.unavailable_reason is not None:
            return self.unavailable_reason
        if self.recovery_ratio is None:
            return AnalysisReasonText("drift excess does not satisfy the declared positive-materiality rule")
        if self.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY:
            return AnalysisReasonText(
                "recovery_ratio is positive but below the declared material recovery-ratio minimum "
                f"({self.material_recovery_ratio_minimum.value})"
            )
        return None


class TemporalAnalysisRecord(StrictModel):
    recovery: TemporalRecoveryResult
    interpretation: TemporalInterpretation

    @model_validator(mode="after")
    def validate_record(self) -> TemporalAnalysisRecord:
        if self.interpretation is not self.recovery.interpretation:
            raise ValueError("temporal interpretation must be derived from the recovery quantities")
        return self


def temporal_recovery(
    *,
    seed: Seed,
    experiment: ExperimentId,
    threshold_method: FederatedThresholdMethod,
    static_reference_cv: MetricValue,
    frozen_future_cv: MetricValue,
    recalibrated_future_cv: MetricValue,
    provenance: TemporalSeedProvenance,
    decision_protocol: TemporalDecisionProtocol,
    mean_fpr_static: MetricValue | None = None,
    mean_fpr_frozen: MetricValue | None = None,
    mean_fpr_recalibrated: MetricValue | None = None,
    client_trajectories: tuple[TemporalClientTrajectory, ...] = (),
    drift_js_frozen_fpr_spearman: TemporalSpearmanDiagnostic | None = None,
    unavailable_reason: AnalysisReasonText | None = None,
) -> TemporalRecoveryResult:
    return TemporalRecoveryResult(
        seed=seed,
        experiment=experiment,
        threshold_method=threshold_method,
        static_reference_cv=static_reference_cv,
        frozen_future_cv=frozen_future_cv,
        recalibrated_future_cv=recalibrated_future_cv,
        decision_protocol=decision_protocol,
        mean_fpr_static=mean_fpr_static,
        mean_fpr_frozen=mean_fpr_frozen,
        mean_fpr_recalibrated=mean_fpr_recalibrated,
        provenance=provenance,
        client_trajectories=client_trajectories,
        drift_js_frozen_fpr_spearman=(
            temporal_drift_fpr_spearman(client_trajectories)
            if drift_js_frozen_fpr_spearman is None
            else drift_js_frozen_fpr_spearman
        ),
        unavailable_reason=unavailable_reason,
    )


def temporal_analysis_record(result: TemporalRecoveryResult) -> TemporalAnalysisRecord:
    return TemporalAnalysisRecord(
        recovery=result,
        interpretation=result.interpretation,
    )


def decide_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
    *,
    required_seed_cohort: SeedCohort = BOUNDED_EVIDENCE_SEED_COHORT,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
    inference_protocol: PairedInferenceProtocol | None = None,
) -> ScientificDecisionResult:

    from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval

    blocked = _blocked_temporal_campaign(records, required_seed_cohort)
    if blocked is not None:
        return blocked
    protocol = inference_protocol or _temporal_inference_protocol(required_seed_cohort)
    defined_ratios = tuple(record.recovery_ratio for record in records if record.recovery_ratio is not None)
    recovery_interval = (
        seed_level_bca_interval(
            defined_ratios,
            protocol=protocol,
            analysis_seed=analysis_seed,
            require_full_cohort=True,
        )
        if len(defined_ratios) == len(records)
        else None
    )
    counts = _temporal_interpretation_counts(records)
    point = recovery_interval.point_estimate if recovery_interval is not None else None
    decision, rationale = _campaign_decision_from_counts(
        counts,
        total=SeedObservationCount(len(records)),
        defined_recovery_count=SeedObservationCount(len(defined_ratios)),
        cohort_size=required_seed_cohort.member_count,
    )
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=decision,
        point_estimate=point,
        interval=recovery_interval,
        rationale=rationale,
    )


@dataclass(frozen=True, slots=True)
class _TemporalInterpretationCounts:
    material_recovery: SeedObservationCount
    partial_or_weak_recovery: SeedObservationCount
    without_recovery: SeedObservationCount
    opposite: SeedObservationCount
    no_degradation: SeedObservationCount
    blocked: SeedObservationCount


def _count_interpretation(
    records: tuple[TemporalRecoveryResult, ...],
    interpretation: TemporalInterpretation,
) -> SeedObservationCount:
    return SeedObservationCount(sum(record.interpretation is interpretation for record in records))


def _temporal_interpretation_counts(
    records: tuple[TemporalRecoveryResult, ...],
) -> _TemporalInterpretationCounts:
    return _TemporalInterpretationCounts(
        material_recovery=_count_interpretation(
            records, TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
        ),
        partial_or_weak_recovery=_count_interpretation(
            records, TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY
        ),
        without_recovery=_count_interpretation(records, TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY),
        opposite=_count_interpretation(records, TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT),
        no_degradation=_count_interpretation(records, TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION),
        blocked=_count_interpretation(records, TemporalInterpretation.BLOCKED_OR_UNAVAILABLE),
    )


def _campaign_decision_from_counts(
    counts: _TemporalInterpretationCounts,
    *,
    total: SeedObservationCount,
    defined_recovery_count: SeedObservationCount,
    cohort_size: SeedCount,
) -> tuple[ScientificDecision, DecisionRationale]:
    if total.value < cohort_size.value or total.value < 2:
        return (
            ScientificDecision.BLOCKED,
            DecisionRationale("publication-level temporal SUPPORTED requires the complete multi-seed declared cohort"),
        )
    if counts.blocked.value > 0:
        return (
            ScientificDecision.BLOCKED,
            DecisionRationale("temporal campaign contains blocked or unavailable seed evidence"),
        )
    if counts.material_recovery == total:
        return (
            ScientificDecision.SUPPORTED,
            DecisionRationale(
                "campaign-level temporal evidence shows material degradation with material "
                "one-shot recalibration recovery on every seed of the declared cohort "
                f"(defined_recovery_ratio_count={defined_recovery_count.value})"
            ),
        )
    if counts.opposite == total:
        return (
            ScientificDecision.OPPOSITE_DIRECTION,
            DecisionRationale("campaign-level temporal evidence moved opposite to the declared degradation direction"),
        )
    if counts.no_degradation == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            DecisionRationale("campaign-level temporal evidence shows no material degradation across the seed cohort"),
        )
    if counts.without_recovery == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            DecisionRationale("campaign-level temporal evidence shows degradation without material recovery"),
        )
    if counts.partial_or_weak_recovery == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            DecisionRationale(
                "campaign-level temporal evidence shows only partial or weak recovery below the material ratio minimum"
            ),
        )
    return (
        ScientificDecision.BOUNDARY_RESULT,
        DecisionRationale(
            "campaign-level temporal evidence is mixed across seeds "
            f"(material_recovery={counts.material_recovery.value}, "
            f"partial_or_weak={counts.partial_or_weak_recovery.value}, "
            f"without={counts.without_recovery.value}, "
            f"no_degradation={counts.no_degradation.value}, opposite={counts.opposite.value}, "
            f"defined_recovery_ratio_count={defined_recovery_count.value})"
        ),
    )


def _blocked_temporal_decision(rationale: DecisionRationale) -> ScientificDecisionResult:
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=ScientificDecision.BLOCKED,
        point_estimate=None,
        interval=None,
        rationale=rationale,
    )


def _blocked_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
    required_seed_cohort: SeedCohort,
) -> ScientificDecisionResult | None:
    if not records:
        return _blocked_temporal_decision(
            DecisionRationale("temporal campaign decision requires the complete declared seed cohort")
        )
    if len({record.experiment for record in records}) != 1 or len({record.threshold_method for record in records}) != 1:
        return _blocked_temporal_decision(
            DecisionRationale("temporal campaign records must share one experiment and threshold method")
        )
    seeds = tuple(record.seed for record in records)
    if len(seeds) != len(frozenset(seeds)):
        return _blocked_temporal_decision(DecisionRationale("temporal campaign records must be unique by seed"))
    if frozenset(seeds) != frozenset(required_seed_cohort.values):
        return _blocked_temporal_decision(
            DecisionRationale("temporal campaign records must equal the complete declared seed cohort")
        )
    if required_seed_cohort.member_count.value < 2:
        return _blocked_temporal_decision(
            DecisionRationale("publication-level temporal decisions require a multi-seed declared cohort")
        )
    provenances = tuple(record.provenance for record in records)
    if any(item.seed != record.seed for item, record in zip(provenances, records, strict=True)):
        return _blocked_temporal_decision(
            DecisionRationale("temporal provenance seeds must match recovery records one-to-one")
        )
    if len({item.population for item in provenances}) != 1:
        return _blocked_temporal_decision(
            DecisionRationale("temporal provenance records must share one population identity")
        )
    return None


def _temporal_inference_protocol(seed_cohort: SeedCohort) -> PairedInferenceProtocol:
    base = CONFIRMATORY_INFERENCE_PROTOCOL
    return PairedInferenceProtocol(
        confidence_level=base.confidence_level,
        paired_seed_count=seed_cohort.member_count,
        interval_method=base.interval_method,
        bootstrap_replicates=base.bootstrap_replicates,
        statistical_test=base.statistical_test,
        wilcoxon_alternative=base.wilcoxon_alternative,
        wilcoxon_zero_method=base.wilcoxon_zero_method,
        wilcoxon_computation_preference=base.wilcoxon_computation_preference,
        effect_size=base.effect_size,
        multiplicity_correction=base.multiplicity_correction,
        descriptive_lower_quantile=base.descriptive_lower_quantile,
        descriptive_upper_quantile=base.descriptive_upper_quantile,
    )


class TemporalSeedSeriesIntervals(StrictModel):
    drift_excess: BootstrapInterval
    recovered_amount: BootstrapInterval
    recovery_ratio: BootstrapInterval | None


def temporal_seed_series_intervals(
    records: tuple[TemporalRecoveryResult, ...],
    *,
    required_seed_cohort: SeedCohort = BOUNDED_EVIDENCE_SEED_COHORT,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> TemporalSeedSeriesIntervals:

    from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval

    protocol = _temporal_inference_protocol(required_seed_cohort)
    drift = seed_level_bca_interval(
        tuple(record.drift_excess for record in records),
        protocol=protocol,
        analysis_seed=analysis_seed,
    )
    recovered = seed_level_bca_interval(
        tuple(record.recovered_amount for record in records),
        protocol=protocol,
        analysis_seed=analysis_seed,
    )
    ratios = tuple(record.recovery_ratio for record in records if record.recovery_ratio is not None)
    recovery_ratio = (
        seed_level_bca_interval(ratios, protocol=protocol, analysis_seed=analysis_seed, require_full_cohort=True)
        if len(ratios) == len(records)
        else None
    )
    return TemporalSeedSeriesIntervals(
        drift_excess=drift,
        recovered_amount=recovered,
        recovery_ratio=recovery_ratio,
    )


class TemporalFutureIdentity(StrictModel):
    split_protocol: SplitProtocolId
    evaluation_role: PartitionRole
    coordinate: TemporalTrainingCoordinate
    evaluation_records: tuple[FederatedScoreRecord, ...]


class TemporalDeploymentProvenance(StrictModel):
    state: TemporalState
    split_protocol: SplitProtocolId
    calibration_role: PartitionRole
    evaluation_role: PartitionRole
    coordinate: TemporalTrainingCoordinate
    calibration_records: tuple[FederatedScoreRecord, ...]
    evaluation_records: tuple[FederatedScoreRecord, ...]

    @model_validator(mode="after")
    def validate_binding(self) -> TemporalDeploymentProvenance:
        if (self.calibration_role, self.evaluation_role) != temporal_partition_roles(self.state):
            raise ValueError("temporal deployment state has an invalid partition binding")
        if self.split_protocol is not temporal_split_protocol(self.state):
            raise ValueError(f"{self.state.name.lower()} requires its designated split protocol")
        if not self.calibration_records or not self.evaluation_records:
            raise ValueError("temporal deployment provenance requires non-empty score evidence")
        if any(record.partition_role is not self.calibration_role for record in self.calibration_records):
            raise ValueError("temporal calibration records must match the declared calibration role")
        if any(record.partition_role is not self.evaluation_role for record in self.evaluation_records):
            raise ValueError("temporal evaluation records must match the declared evaluation role")
        coordinate = training_coordinates(self.coordinate)
        if any(record.coordinate not in coordinate for record in self.calibration_records + self.evaluation_records):
            raise ValueError("temporal score records must match the declared detector coordinate")
        clients = tuple(record.scored_client for record in self.calibration_records + self.evaluation_records)
        if any(client.population is not coordinate[0].population for client in clients):
            raise ValueError("temporal score records must match the detector population")
        return self

    @property
    def future_identity(self) -> TemporalFutureIdentity:
        return TemporalFutureIdentity(
            split_protocol=self.split_protocol,
            evaluation_role=self.evaluation_role,
            coordinate=self.coordinate,
            evaluation_records=self.evaluation_records,
        )

    @classmethod
    def from_score_manifest(
        cls,
        state: TemporalState,
        manifest: ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity],
    ) -> TemporalDeploymentProvenance:
        calibration_role, evaluation_role = temporal_partition_roles(state)
        if not manifest.records_for(calibration_role) or not manifest.records_for(evaluation_role):
            raise ScientificContractError(
                ErrorMessage("temporal provenance requires non-empty calibration and evaluation score sets"),
                subject=state,
            )
        return cls(
            state=state,
            split_protocol=manifest.scored_split_protocol,
            calibration_role=calibration_role,
            evaluation_role=evaluation_role,
            coordinate=manifest.coordinate,
            calibration_records=tuple(manifest.records_for(calibration_role)),
            evaluation_records=tuple(manifest.records_for(evaluation_role)),
        )

    def validate_score_manifest(
        self,
        manifest: ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity],
    ) -> None:
        if TemporalDeploymentProvenance.from_score_manifest(self.state, manifest) != self:
            raise ScientificContractError(
                ErrorMessage("temporal deployment provenance does not match immutable score artifacts"),
                subject=self.state,
                reason=TemporalProvenanceViolation.SCORE_EVIDENCE_CHANGED,
            )


def validate_frozen_recalibrated_pair(
    frozen: TemporalDeploymentProvenance,
    recalibrated: TemporalDeploymentProvenance,
) -> None:

    if frozen.state is not TemporalState.FROZEN_FUTURE or recalibrated.state is not TemporalState.RECALIBRATED_FUTURE:
        raise ScientificContractError(
            ErrorMessage("temporal comparison requires frozen and recalibrated future states"),
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )
    if frozen.future_identity != recalibrated.future_identity:
        raise ScientificContractError(
            ErrorMessage("frozen and recalibrated future must share detector, split, and evaluation scores"),
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )


def temporal_partition_roles(state: TemporalState) -> tuple[PartitionRole, PartitionRole]:
    match state:
        case TemporalState.STATIC_REFERENCE | TemporalState.FROZEN_FUTURE:
            return PartitionRole.CALIBRATION, PartitionRole.EVALUATION
        case TemporalState.RECALIBRATED_FUTURE:
            return PartitionRole.FUTURE_RECALIBRATION, PartitionRole.EVALUATION
    raise ValueError(f"unsupported temporal state: {state}")


def temporal_split_protocol(state: TemporalState) -> SplitProtocolId:
    match state:
        case TemporalState.STATIC_REFERENCE:
            return SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
        case TemporalState.FROZEN_FUTURE | TemporalState.RECALIBRATED_FUTURE:
            return SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    raise ValueError(f"unsupported temporal state: {state}")


def training_coordinates(coordinate: TemporalTrainingCoordinate) -> tuple[FederatedTrainingCoordinate, ...]:
    return coordinate if isinstance(coordinate, tuple) else (coordinate,)


class TemporalDecisionProtocol(StrictModel):
    drift_excess_materiality_threshold: MetricValue
    material_recovery_ratio_minimum: Ratio
    seed_cohort: SeedCohort
    undefined_recovery_when_drift_not_material: bool
    mixed_seed_publication_support: bool
    require_full_seed_provenance: bool
    require_uncertainty_for_supported: bool

    @model_validator(mode="after")
    def validate_protocol(self) -> TemporalDecisionProtocol:
        if self.drift_excess_materiality_threshold.value <= 0.0:
            raise ValueError("temporal drift-excess materiality threshold must be positive")
        if self.material_recovery_ratio_minimum.value <= 0.0:
            raise ValueError("temporal material recovery-ratio minimum must be positive")
        if self.seed_cohort.member_count.value < 2:
            raise ValueError("temporal publication decisions require a multi-seed cohort")
        if not self.undefined_recovery_when_drift_not_material:
            raise ValueError("temporal protocol must leave recovery undefined when drift is non-material")
        if self.mixed_seed_publication_support:
            raise ValueError("mixed-seed temporal evidence cannot support a publication claim")
        if not self.require_full_seed_provenance:
            raise ValueError("temporal publication requires full per-seed provenance")
        return self


LOCKED_TEMPORAL_DECISION_PROTOCOL = TemporalDecisionProtocol(
    drift_excess_materiality_threshold=MetricValue(0.05),
    material_recovery_ratio_minimum=Ratio(0.5),
    seed_cohort=BOUNDED_EVIDENCE_SEED_COHORT,
    undefined_recovery_when_drift_not_material=True,
    mixed_seed_publication_support=False,
    require_full_seed_provenance=True,
    require_uncertainty_for_supported=True,
)


def require_temporal_decision_protocol() -> TemporalDecisionProtocol:
    return LOCKED_TEMPORAL_DECISION_PROTOCOL
