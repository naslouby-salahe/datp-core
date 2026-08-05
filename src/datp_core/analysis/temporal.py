"""Typed temporal quantities and immutable deployment provenance."""

from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.decisions import ScientificDecisionResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PartitionRole,
    ScientificDecision,
    SplitProtocolId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.protocols.inference import ScoreArtifactManifest
from datp_core.protocols.metrics import TEMPORAL_CV_MATERIALITY_CUTOFF


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_RECOVERY = "temporal_degradation_with_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"


class TemporalRecoveryResult(StrictModel):
    seed: Seed
    static_reference_cv: MetricValue
    frozen_future_cv: MetricValue
    recalibrated_future_cv: MetricValue

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
    def materiality_cutoff(self) -> MetricValue:
        return TEMPORAL_CV_MATERIALITY_CUTOFF

    @property
    def recovery_ratio(self) -> MetricValue | None:
        if self.drift_excess.value <= self.materiality_cutoff.value:
            return None
        return MetricValue(self.recovered_amount.value / self.drift_excess.value)

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.UNDEFINED if self.recovery_ratio is None else AvailabilityStatus.AVAILABLE

    @property
    def interpretation(self) -> TemporalInterpretation:
        if self.recovery_ratio is None:
            if self.drift_excess.value < 0.0:
                return TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
            return TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
        if self.recovered_amount.value > 0.0:
            return TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY
        return TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY

    @property
    def reason(self) -> str | None:
        return (
            None
            if self.recovery_ratio is not None
            else "drift excess does not satisfy the declared positive-materiality rule"
        )


class TemporalAnalysisRecord(StrictModel):
    recovery: TemporalRecoveryResult
    interpretation: TemporalInterpretation
    decision: ScientificDecisionResult

    @model_validator(mode="after")
    def validate_record(self) -> "TemporalAnalysisRecord":
        if self.interpretation is not self.recovery.interpretation:
            raise ValueError("temporal interpretation must be derived from the recovery quantities")
        if self.decision.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal decisions must remain temporal-boundary evidence")
        if self.decision.point_estimate != self.recovery.recovery_ratio:
            raise ValueError("temporal decision estimate must equal the recovery ratio")
        return self


class TemporalFutureIdentity(StrictModel):
    split_protocol: SplitProtocolId
    evaluation_role: PartitionRole
    coordinate_checksum: Checksum
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    evaluation_score_set_checksum: Checksum


class TemporalDeploymentProvenance(StrictModel):
    """Immutable calibration/evaluation binding for one temporal state."""

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
    def validate_binding(self) -> "TemporalDeploymentProvenance":
        if (self.calibration_role, self.evaluation_role) != _partition_roles(self.state):
            raise ValueError("temporal deployment state has an invalid partition binding")
        if self.split_protocol is not _split_protocol(self.state):
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
    def from_score_manifest(
        cls,
        state: TemporalState,
        manifest: ScoreArtifactManifest,
    ) -> "TemporalDeploymentProvenance":
        calibration_role, evaluation_role = _partition_roles(state)
        if not manifest.records_for(calibration_role) or not manifest.records_for(evaluation_role):
            raise ScientificContractError(
                "temporal provenance requires non-empty calibration and evaluation score sets",
                subject=state,
            )
        return cls(
            state=state,
            split_protocol=manifest.coordinate.split_protocol,
            calibration_role=calibration_role,
            evaluation_role=evaluation_role,
            coordinate_checksum=canonical_checksum(manifest.coordinate),
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            calibration_score_set_checksum=manifest.score_set_checksum(calibration_role),
            evaluation_score_set_checksum=manifest.score_set_checksum(evaluation_role),
        )

    def validate_score_manifest(self, manifest: ScoreArtifactManifest) -> None:
        if TemporalDeploymentProvenance.from_score_manifest(self.state, manifest) != self:
            raise ScientificContractError(
                "temporal deployment provenance does not match immutable score artifacts",
                subject=self.state,
                reason="calibration, evaluation, model, preprocessing, or split evidence changed",
            )


def validate_frozen_recalibrated_pair(
    frozen: TemporalDeploymentProvenance,
    recalibrated: TemporalDeploymentProvenance,
) -> None:
    """Only the calibration window may differ."""
    if frozen.state is not TemporalState.FROZEN_FUTURE or recalibrated.state is not TemporalState.RECALIBRATED_FUTURE:
        raise ScientificContractError(
            "temporal comparison requires frozen and recalibrated future states",
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )
    if frozen.future_identity != recalibrated.future_identity:
        raise ScientificContractError(
            "frozen and recalibrated future must share detector, split, and evaluation scores",
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )


def temporal_recovery(
    *,
    seed: Seed,
    static_reference_cv: MetricValue,
    frozen_future_cv: MetricValue,
    recalibrated_future_cv: MetricValue,
) -> TemporalRecoveryResult:
    return TemporalRecoveryResult(
        seed=seed,
        static_reference_cv=static_reference_cv,
        frozen_future_cv=frozen_future_cv,
        recalibrated_future_cv=recalibrated_future_cv,
    )


def decide_temporal(result: TemporalRecoveryResult) -> ScientificDecisionResult:
    match result.interpretation:
        case TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY:
            decision = ScientificDecision.SUPPORTED
            rationale = "temporal degradation has positive one-shot recalibration recovery"
        case TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY:
            decision = ScientificDecision.BOUNDARY_RESULT
            rationale = "temporal degradation has no positive one-shot recalibration recovery"
        case TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION:
            decision = ScientificDecision.BOUNDARY_RESULT
            rationale = "no materially positive temporal degradation was detected"
        case TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT:
            decision = ScientificDecision.OPPOSITE_DIRECTION
            rationale = "future CV(FPR) moved opposite to the declared degradation direction"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=decision,
        point_estimate=result.recovery_ratio,
        interval=None,
        rationale=rationale,
    )


def temporal_analysis_record(result: TemporalRecoveryResult) -> TemporalAnalysisRecord:
    return TemporalAnalysisRecord(
        recovery=result,
        interpretation=result.interpretation,
        decision=decide_temporal(result),
    )


def _partition_roles(state: TemporalState) -> tuple[PartitionRole, PartitionRole]:
    match state:
        case TemporalState.STATIC_REFERENCE | TemporalState.FROZEN_FUTURE:
            return PartitionRole.CALIBRATION, PartitionRole.EVALUATION
        case TemporalState.RECALIBRATED_FUTURE:
            return PartitionRole.FUTURE_RECALIBRATION, PartitionRole.EVALUATION
    raise ValueError(f"unsupported temporal state: {state}")


def _split_protocol(state: TemporalState) -> SplitProtocolId:
    match state:
        case TemporalState.STATIC_REFERENCE:
            return SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
        case TemporalState.FROZEN_FUTURE | TemporalState.RECALIBRATED_FUTURE:
            return SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    raise ValueError(f"unsupported temporal state: {state}")
