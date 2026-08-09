"""Typed temporal recovery quantities and campaign-level scientific interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_checksum
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
    SplitProtocolId,
    TemporalState,
)
from datp_core.core.numeric import MetricValue, Ratio, Seed, SeedCount, SeedObservationCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import (
    ClientIdentityContract,
    ScoreArtifactManifest,
    TrainingCoordinateContract,
)
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


class TemporalProvenanceViolation(StrEnum):
    SCORE_EVIDENCE_CHANGED = "score_evidence_changed"


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
    unavailable_reasons: tuple[AnalysisReasonText, ...] = ()

    @model_validator(mode="after")
    def validate_bindings(self) -> TemporalSeedProvenance:
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
    """Per-seed temporal quantities. Never carries a publication-level SUPPORTED decision."""

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


def _temporal_interpretation_counts(
    records: tuple[TemporalRecoveryResult, ...],
) -> _TemporalInterpretationCounts:
    return _TemporalInterpretationCounts(
        material_recovery=SeedObservationCount(
            sum(
                record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
                for record in records
            )
        ),
        partial_or_weak_recovery=SeedObservationCount(
            sum(
                record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY
                for record in records
            )
        ),
        without_recovery=SeedObservationCount(
            sum(
                record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY
                for record in records
            )
        ),
        opposite=SeedObservationCount(
            sum(record.interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT for record in records)
        ),
        no_degradation=SeedObservationCount(
            sum(
                record.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
                for record in records
            )
        ),
        blocked=SeedObservationCount(
            sum(record.interpretation is TemporalInterpretation.BLOCKED_OR_UNAVAILABLE for record in records)
        ),
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
            DecisionRationale(
                "campaign-level temporal evidence moved opposite to the declared degradation direction"
            ),
        )
    if counts.no_degradation == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            DecisionRationale(
                "campaign-level temporal evidence shows no material degradation across the seed cohort"
            ),
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
            rationale=DecisionRationale("temporal campaign decision requires the complete declared seed cohort"),
        )
    if len({record.experiment for record in records}) != 1 or len({record.threshold_method for record in records}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale(
                "temporal campaign records must share one experiment and threshold method"
            ),
        )
    seeds = tuple(record.seed for record in records)
    if len(seeds) != len(frozenset(seeds)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("temporal campaign records must be unique by seed"),
        )
    if frozenset(seeds) != frozenset(required_seed_cohort.values):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale(
                "temporal campaign records must equal the complete declared seed cohort"
            ),
        )
    if required_seed_cohort.member_count.value < 2:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale(
                "publication-level temporal decisions require a multi-seed declared cohort"
            ),
        )
    provenances = tuple(record.provenance for record in records)
    if any(item.seed != record.seed for item, record in zip(provenances, records, strict=True)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("temporal provenance seeds must match recovery records one-to-one"),
        )
    if len({item.population for item in provenances}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("temporal provenance records must share one population identity"),
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
            rationale=DecisionRationale("temporal provenance must not be cloned across seeds"),
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


def temporal_seed_series_intervals(
    records: tuple[TemporalRecoveryResult, ...],
    *,
    required_seed_cohort: SeedCohort = BOUNDED_EVIDENCE_SEED_COHORT,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> tuple[BootstrapInterval, BootstrapInterval | None, BootstrapInterval | None]:
    """BCa over seed-level drift excess, recovery amount, and recovery ratio when defined."""
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
    return drift, recovered, recovery_ratio


class TemporalFutureIdentity(StrictModel):
    split_protocol: SplitProtocolId
    evaluation_role: PartitionRole
    coordinate_checksum: Checksum
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    evaluation_score_set_checksum: Checksum


class TemporalDeploymentProvenance(StrictModel):
    """Immutable calibration/evaluation binding for one temporal deployment state."""

    state: TemporalState
    split_protocol: SplitProtocolId
    calibration_role: PartitionRole
    evaluation_role: PartitionRole
    coordinate_checksum: Checksum
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    calibration_score_set_checksum: Checksum
    evaluation_score_set_checksum: Checksum

    @model_validator(mode="after")
    def validate_binding(self) -> TemporalDeploymentProvenance:
        if (self.calibration_role, self.evaluation_role) != temporal_partition_roles(self.state):
            raise ValueError("temporal deployment state has an invalid partition binding")
        if self.split_protocol is not temporal_split_protocol(self.state):
            raise ValueError(f"{self.state.name.lower()} requires its designated split protocol")
        return self

    @property
    def future_identity(self) -> TemporalFutureIdentity:
        return TemporalFutureIdentity(
            split_protocol=self.split_protocol,
            evaluation_role=self.evaluation_role,
            coordinate_checksum=self.coordinate_checksum,
            checkpoint_checksum=self.checkpoint_checksum,
            preprocessing_state_set_checksum=self.preprocessing_state_set_checksum,
            split_manifest_checksum=self.split_manifest_checksum,
            evaluation_score_set_checksum=self.evaluation_score_set_checksum,
        )

    @classmethod
    def from_score_manifest[CoordinateT: TrainingCoordinateContract, ClientT: ClientIdentityContract](
        cls,
        state: TemporalState,
        manifest: ScoreArtifactManifest[CoordinateT, ClientT],
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
            coordinate_checksum=canonical_checksum(manifest.coordinate),
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            calibration_score_set_checksum=manifest.score_set_checksum(calibration_role),
            evaluation_score_set_checksum=manifest.score_set_checksum(evaluation_role),
        )

    def validate_score_manifest[
        CoordinateT: TrainingCoordinateContract,
        ClientT: ClientIdentityContract,
    ](
        self,
        manifest: ScoreArtifactManifest[CoordinateT, ClientT],
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
    """Require identical future detector and evaluation evidence across recalibration states."""
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


class TemporalDecisionProtocol(StrictModel):
    """Explicit temporal interpretation thresholds and publication guards."""

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


# drift_excess_materiality_threshold reuses the CV(FPR) indistinguishability magnitude used for Ditto absorption.
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
