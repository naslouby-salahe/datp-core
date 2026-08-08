"""Typed temporal recovery quantities and campaign-level scientific interpretation."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TemporalState,
)
from datp_core.core.numeric import MetricValue, Ratio, Seed
from datp_core.analysis.inference.wilcoxon import PairedInferenceProtocol
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.protocols.temporal import TemporalDecisionProtocol, TemporalDeploymentProvenance


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY = "temporal_degradation_with_material_recovery"
    TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY = "temporal_degradation_with_partial_or_weak_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"
    BLOCKED_OR_UNAVAILABLE = "blocked_or_unavailable"


class TemporalSeedProvenance(StrictModel):
    """Exact one-seed temporal artifact provenance for campaign identity."""

    seed: Seed
    experiment: ExperimentId
    population: PopulationId
    threshold_method: FederatedThresholdMethod
    static_reference: TemporalDeploymentProvenance
    frozen_future: TemporalDeploymentProvenance
    recalibrated_future: TemporalDeploymentProvenance
    static_threshold_checksum: Checksum
    frozen_threshold_checksum: Checksum
    recalibrated_threshold_checksum: Checksum
    static_evaluation_checksum: Checksum
    frozen_evaluation_checksum: Checksum
    recalibrated_evaluation_checksum: Checksum
    client_inventory_checksum: Checksum
    eligibility_checksum: Checksum
    source_row_checksum: Checksum
    row_order_checksum: Checksum
    excluded_clients: tuple[ClientIdentity, ...] = ()
    unavailable_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_bindings(self) -> "TemporalSeedProvenance":
        if self.static_reference.state is not TemporalState.STATIC_REFERENCE:
            raise ValueError("static_reference provenance must use the static_reference state")
        if self.frozen_future.state is not TemporalState.FROZEN_FUTURE:
            raise ValueError("frozen_future provenance must use the frozen_future state")
        if self.recalibrated_future.state is not TemporalState.RECALIBRATED_FUTURE:
            raise ValueError("recalibrated_future provenance must use the recalibrated_future state")
        if (
            self.static_reference.checkpoint_checksum != self.frozen_future.checkpoint_checksum
            or self.static_reference.preprocessing_state_set_checksum
            != self.frozen_future.preprocessing_state_set_checksum
        ):
            raise ValueError("static and frozen temporal states must share detector and preprocessing identity")
        if self.frozen_future.future_identity != self.recalibrated_future.future_identity:
            raise ValueError("frozen and recalibrated future must share detector, split, and evaluation scores")
        if any(client.population is not self.population for client in self.excluded_clients):
            raise ValueError("temporal exclusions must match the provenance population")
        if len(self.excluded_clients) != len(frozenset(self.excluded_clients)):
            raise ValueError("temporal excluded clients must be unique")
        return self


class TemporalClientTrajectory(StrictModel):
    """Per-client temporal state trajectory for one seed and threshold method."""

    seed: Seed
    client: ClientIdentity
    threshold_method: FederatedThresholdMethod
    eligible: bool
    exclusion_reason: str | None
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

    @property
    def client_id(self) -> str:
        return self.client.client_id

    @property
    def threshold_movement_frozen(self) -> MetricValue | None:
        if self.threshold_static is None or self.threshold_frozen is None:
            return None
        return MetricValue(self.threshold_frozen.value - self.threshold_static.value)

    @property
    def threshold_movement_recalibrated(self) -> MetricValue | None:
        if self.threshold_frozen is None or self.threshold_recalibrated is None:
            return None
        return MetricValue(self.threshold_recalibrated.value - self.threshold_frozen.value)

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
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def validate_recovery(self) -> "TemporalRecoveryResult":
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
    def drift_excess_materiality_threshold(self) -> MetricValue:
        return self.decision_protocol.drift_excess_materiality_threshold

    @property
    def material_recovery_ratio_minimum(self) -> Ratio:
        return self.decision_protocol.material_recovery_ratio_minimum

    @property
    def recovery_ratio(self) -> MetricValue | None:
        if self.unavailable_reason is not None:
            return None
        if self.drift_excess.value <= self.drift_excess_materiality_threshold.value:
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
    def reason(self) -> str | None:
        if self.unavailable_reason is not None:
            return self.unavailable_reason
        if self.recovery_ratio is None:
            return "drift excess does not satisfy the declared positive-materiality rule"
        if self.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY:
            return (
                "recovery_ratio is positive but below the declared material recovery-ratio minimum "
                f"({self.material_recovery_ratio_minimum.value})"
            )
        return None


class TemporalAnalysisRecord(StrictModel):
    """Per-seed temporal quantities. Never carries a publication-level SUPPORTED decision."""

    recovery: TemporalRecoveryResult
    interpretation: TemporalInterpretation

    @model_validator(mode="after")
    def validate_record(self) -> "TemporalAnalysisRecord":
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
    unavailable_reason: str | None = None,
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
    """One campaign-level decision over the complete declared temporal seed cohort."""
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
        total=len(records),
        defined_recovery_count=len(defined_ratios),
        cohort_size=required_seed_cohort.member_count.value,
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
    material_recovery: int
    partial_or_weak_recovery: int
    without_recovery: int
    opposite: int
    no_degradation: int
    blocked: int


def _temporal_interpretation_counts(
    records: tuple[TemporalRecoveryResult, ...],
) -> _TemporalInterpretationCounts:
    return _TemporalInterpretationCounts(
        material_recovery=sum(
            record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
            for record in records
        ),
        partial_or_weak_recovery=sum(
            record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY
            for record in records
        ),
        without_recovery=sum(
            record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY for record in records
        ),
        opposite=sum(record.interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT for record in records),
        no_degradation=sum(
            record.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION for record in records
        ),
        blocked=sum(record.interpretation is TemporalInterpretation.BLOCKED_OR_UNAVAILABLE for record in records),
    )


def _campaign_decision_from_counts(
    counts: _TemporalInterpretationCounts,
    *,
    total: int,
    defined_recovery_count: int,
    cohort_size: int,
) -> tuple[ScientificDecision, str]:
    if total < cohort_size or total < 2:
        return (
            ScientificDecision.BLOCKED,
            "publication-level temporal SUPPORTED requires the complete multi-seed declared cohort",
        )
    if counts.blocked > 0:
        return (
            ScientificDecision.BLOCKED,
            "temporal campaign contains blocked or unavailable seed evidence",
        )
    if counts.material_recovery == total:
        return (
            ScientificDecision.SUPPORTED,
            "campaign-level temporal evidence shows material degradation with material "
            f"one-shot recalibration recovery on every seed of the declared cohort "
            f"(defined_recovery_ratio_count={defined_recovery_count})",
        )
    if counts.opposite == total:
        return (
            ScientificDecision.OPPOSITE_DIRECTION,
            "campaign-level temporal evidence moved opposite to the declared degradation direction",
        )
    if counts.no_degradation == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            "campaign-level temporal evidence shows no material degradation across the seed cohort",
        )
    if counts.without_recovery == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            "campaign-level temporal evidence shows degradation without material recovery",
        )
    if counts.partial_or_weak_recovery == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            "campaign-level temporal evidence shows only partial or weak recovery below the material ratio minimum",
        )
    return (
        ScientificDecision.BOUNDARY_RESULT,
        (
            "campaign-level temporal evidence is mixed across seeds "
            f"(material_recovery={counts.material_recovery}, "
            f"partial_or_weak={counts.partial_or_weak_recovery}, "
            f"without={counts.without_recovery}, "
            f"no_degradation={counts.no_degradation}, opposite={counts.opposite}, "
            f"defined_recovery_ratio_count={defined_recovery_count})"
        ),
    )


def _blocked_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
    required_seed_cohort: SeedCohort,
) -> ScientificDecisionResult | None:
    if not records:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign decision requires the complete declared seed cohort",
        )
    if len({record.experiment for record in records}) != 1 or len({record.threshold_method for record in records}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign records must share one experiment and threshold method",
        )
    seeds = tuple(record.seed for record in records)
    if len(seeds) != len(frozenset(seeds)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign records must be unique by seed",
        )
    if frozenset(seeds) != frozenset(required_seed_cohort.values):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign records must equal the complete declared seed cohort",
        )
    if required_seed_cohort.member_count.value < 2:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="publication-level temporal decisions require a multi-seed declared cohort",
        )
    provenances = tuple(record.provenance for record in records)
    if any(item.seed != record.seed for item, record in zip(provenances, records, strict=True)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal provenance seeds must match recovery records one-to-one",
        )
    if len({item.population for item in provenances}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal provenance records must share one population identity",
        )
    checksum_keys = tuple(
        (
            item.static_reference.checkpoint_checksum,
            item.static_reference.split_manifest_checksum,
            item.frozen_future.evaluation_score_set_checksum,
            item.recalibrated_future.calibration_score_set_checksum,
            item.static_threshold_checksum,
            item.frozen_threshold_checksum,
            item.recalibrated_threshold_checksum,
            item.static_evaluation_checksum,
            item.frozen_evaluation_checksum,
            item.recalibrated_evaluation_checksum,
            item.client_inventory_checksum,
            item.eligibility_checksum,
            item.source_row_checksum,
            item.row_order_checksum,
        )
        for item in provenances
    )
    if len(frozenset(checksum_keys)) != len(checksum_keys):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal provenance must not be cloned across seeds",
        )
    return None


def _temporal_inference_protocol(seed_cohort: SeedCohort) -> PairedInferenceProtocol:
    base = CONFIRMATORY_INFERENCE_PROTOCOL
    return PairedInferenceProtocol(
        confidence_level=base.confidence_level,
        seed_cohort=seed_cohort,
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


def temporal_seed_series_intervals(
    records: tuple[TemporalRecoveryResult, ...],
    *,
    required_seed_cohort: SeedCohort = BOUNDED_EVIDENCE_SEED_COHORT,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> tuple[BootstrapInterval, BootstrapInterval | None, BootstrapInterval | None]:
    """BCa over seed-level drift excess, recovery amount, and recovery ratio when defined."""
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
    return drift, recovered, recovery_ratio
