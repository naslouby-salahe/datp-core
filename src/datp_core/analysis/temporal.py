"""Typed temporal quantities only; this module never executes temporal experiments."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.analysis.inference.bootstrap import ScientificDecisionResult
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PartitionRole,
    ScientificDecision,
    SplitProtocolId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, Seed, checksum_text
from datp_core.protocols.metrics import TEMPORAL_CV_MATERIALITY_CUTOFF
from datp_core.scoring.models import ScoreArtifactManifest, ScoreRecord


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_RECOVERY = "temporal_degradation_with_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"
    BLOCKED_MATERIALITY_DECISION = "blocked_materiality_decision"


@dataclass(frozen=True, slots=True)
class TemporalRecoveryResult:
    evidence_role: EvidenceRole
    seed: Seed
    static_reference_cv: MetricValue
    frozen_future_cv: MetricValue
    recalibrated_future_cv: MetricValue
    drift_excess: MetricValue
    recovered_amount: MetricValue
    recovery_ratio: MetricValue | None
    materiality_cutoff: MetricValue
    availability: AvailabilityStatus
    interpretation: TemporalInterpretation
    reason: str

    def __post_init__(self) -> None:
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal recovery requires temporal-boundary evidence")
        if self.availability is AvailabilityStatus.AVAILABLE and self.recovery_ratio is None:
            raise ValueError("available temporal recovery requires a ratio")
        if self.availability is not AvailabilityStatus.AVAILABLE and (
            self.recovery_ratio is not None or not self.reason
        ):
            raise ValueError("unavailable temporal recovery requires an explicit reason")


@dataclass(frozen=True, slots=True)
class TemporalDeploymentProvenance:
    """Immutable calibration/evaluation binding for one declared temporal state."""

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

    def __post_init__(self) -> None:
        expected = _expected_partition_roles(self.state)
        if (self.calibration_role, self.evaluation_role) != expected:
            raise ValueError("temporal deployment state has an invalid calibration/evaluation partition binding")
        if self.state is TemporalState.STATIC_REFERENCE:
            if self.split_protocol is not SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE:
                raise ValueError("static reference requires its random-fractional split protocol")
        elif self.split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
            raise ValueError("future deployment states require the chronological temporal split protocol")

    @classmethod
    def from_score_manifest(
        cls,
        state: TemporalState,
        manifest: ScoreArtifactManifest,
    ) -> "TemporalDeploymentProvenance":
        calibration_role, evaluation_role = _expected_partition_roles(state)
        calibration_records = manifest.records_for(calibration_role)
        evaluation_records = manifest.records_for(evaluation_role)
        return cls(
            state=state,
            split_protocol=manifest.coordinate.split_protocol,
            calibration_role=calibration_role,
            evaluation_role=evaluation_role,
            coordinate_checksum=checksum_text(repr(manifest.coordinate)),
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            calibration_score_set_checksum=_score_set_checksum(calibration_records),
            evaluation_score_set_checksum=_score_set_checksum(evaluation_records),
        )

    def validate_score_manifest(self, manifest: ScoreArtifactManifest) -> None:
        observed = TemporalDeploymentProvenance.from_score_manifest(self.state, manifest)
        if observed != self:
            raise ScientificContractError(
                "temporal deployment provenance does not match immutable score artifacts",
                subject=self.state,
                reason="calibration, evaluation, model, preprocessing, or split evidence changed",
            )


def validate_frozen_recalibrated_pair(
    frozen: TemporalDeploymentProvenance,
    recalibrated: TemporalDeploymentProvenance,
) -> None:
    """Only the calibration window may differ between frozen and recalibrated future."""
    if frozen.state is not TemporalState.FROZEN_FUTURE or recalibrated.state is not TemporalState.RECALIBRATED_FUTURE:
        raise ScientificContractError(
            "temporal comparison requires frozen and recalibrated future states",
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )
    fixed_fields = ( # TODO: this should be an enum of fields in the codebase, not a magic tuple
        "split_protocol",
        "evaluation_role",
        "coordinate_checksum",
        "checkpoint_checksum",
        "preprocessing_state_set_checksum",
        "split_manifest_checksum",
        "evaluation_score_set_checksum",
    )
    if any(getattr(frozen, field) != getattr(recalibrated, field) for field in fixed_fields):
        raise ScientificContractError(
            "frozen and recalibrated future must share detector, split, and future evaluation scores",
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )


def _expected_partition_roles(state: TemporalState) -> tuple[PartitionRole, PartitionRole]:
    match state:
        case TemporalState.STATIC_REFERENCE | TemporalState.FROZEN_FUTURE:
            return PartitionRole.CALIBRATION, PartitionRole.EVALUATION
        case TemporalState.RECALIBRATED_FUTURE:
            return PartitionRole.FUTURE_RECALIBRATION, PartitionRole.EVALUATION


def _score_set_checksum(records: tuple[ScoreRecord, ...]) -> Checksum:
    entries = sorted(f"{record.scored_client.client_id}:{record.checksum.value}" for record in records)
    return checksum_text("|".join(entries))


def temporal_recovery(
    *,
    seed: Seed,
    static_reference_cv: MetricValue,
    frozen_future_cv: MetricValue,
    recalibrated_future_cv: MetricValue,
) -> TemporalRecoveryResult:
    drift_excess = MetricValue(frozen_future_cv.value - static_reference_cv.value)
    recovered_amount = MetricValue(frozen_future_cv.value - recalibrated_future_cv.value)
    if drift_excess > TEMPORAL_CV_MATERIALITY_CUTOFF:
        return TemporalRecoveryResult(
            EvidenceRole.TEMPORAL_BOUNDARY,
            seed,
            static_reference_cv,
            frozen_future_cv,
            recalibrated_future_cv,
            drift_excess,
            recovered_amount,
            MetricValue(recovered_amount.value / drift_excess.value),
            TEMPORAL_CV_MATERIALITY_CUTOFF,
            AvailabilityStatus.AVAILABLE,
            _available_interpretation(recovered_amount),
            "",
        )
    return TemporalRecoveryResult(
        EvidenceRole.TEMPORAL_BOUNDARY,
        seed,
        static_reference_cv,
        frozen_future_cv,
        recalibrated_future_cv,
        drift_excess,
        recovered_amount,
        None,
        TEMPORAL_CV_MATERIALITY_CUTOFF,
        AvailabilityStatus.UNDEFINED,
        _undefined_interpretation(drift_excess),
        "drift excess does not satisfy the declared positive-materiality rule",
    )


def _available_interpretation(recovered_amount: MetricValue) -> TemporalInterpretation:
    if recovered_amount > 0:
        return TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY
    return TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY


def _undefined_interpretation(drift_excess: MetricValue) -> TemporalInterpretation:
    if drift_excess < 0:
        return TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
    return TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION


def decide_temporal(result: TemporalRecoveryResult) -> ScientificDecisionResult:
    if result.availability is not AvailabilityStatus.AVAILABLE or result.recovery_ratio is None:
        return ScientificDecisionResult(
            EvidenceRole.TEMPORAL_BOUNDARY,
            ScientificDecision.BLOCKED,
            None,
            None,
            AvailabilityStatus.UNAVAILABLE,
            result.reason,
        )
    if result.recovered_amount > 0:
        return ScientificDecisionResult(
            EvidenceRole.TEMPORAL_BOUNDARY,
            ScientificDecision.SUPPORTED,
            result.recovery_ratio,
            None,
            AvailabilityStatus.AVAILABLE,
            "temporal degradation has positive one-shot recalibration recovery",
        )
    return ScientificDecisionResult(
        EvidenceRole.TEMPORAL_BOUNDARY,
        ScientificDecision.BOUNDARY_RESULT,
        result.recovery_ratio,
        None,
        AvailabilityStatus.AVAILABLE,
        "temporal degradation has no positive one-shot recalibration recovery",
    )
