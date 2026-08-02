"""Typed temporal quantities only; this module never executes experiments."""

import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum, StrEnum
from math import isfinite

from datp_core.analysis.models import ScientificDecisionResult
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PartitionRole,
    ScientificDecision,
    SplitProtocolId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    MetricValue,
    Seed,
    checksum_text,
)
from datp_core.protocols.metrics import (
    TEMPORAL_CV_MATERIALITY_CUTOFF,
)
from datp_core.scoring.models import (
    ScoreArtifactManifest,
    ScoreRecord,
)


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_RECOVERY = "temporal_degradation_with_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"


@dataclass(frozen=True, slots=True)
class TemporalRecoveryResult:
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
        if self.recovery_ratio is None:
            return AvailabilityStatus.UNDEFINED
        return AvailabilityStatus.AVAILABLE

    @property
    def interpretation(self) -> TemporalInterpretation:
        if self.recovery_ratio is not None:
            if self.recovered_amount.value > 0.0:
                return TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY
            return TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY
        if self.drift_excess.value < 0.0:
            return TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
        return TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION

    @property
    def reason(self) -> str:
        if self.recovery_ratio is not None:
            return ""
        return "drift excess does not satisfy the declared positive-materiality rule"


@dataclass(frozen=True, slots=True)
class TemporalFutureIdentity:
    split_protocol: SplitProtocolId
    evaluation_role: PartitionRole
    coordinate_checksum: Checksum
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    evaluation_score_set_checksum: Checksum


@dataclass(frozen=True, slots=True)
class TemporalDeploymentProvenance:
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

    def __post_init__(self) -> None:
        expected_roles = _expected_partition_roles(self.state)
        if (
            self.calibration_role,
            self.evaluation_role,
        ) != expected_roles:
            raise ValueError("temporal deployment state has an invalid partition binding")

        if self.state is TemporalState.STATIC_REFERENCE:
            if self.split_protocol is not SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE:
                raise ValueError("static reference requires its random-fractional split protocol")
        elif self.split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
            raise ValueError("future deployment states require the chronological split protocol")

    @property
    def future_identity(self) -> TemporalFutureIdentity:
        return TemporalFutureIdentity(
            split_protocol=self.split_protocol,
            evaluation_role=self.evaluation_role,
            coordinate_checksum=self.coordinate_checksum,
            checkpoint_checksum=self.checkpoint_checksum,
            preprocessing_state_set_checksum=(self.preprocessing_state_set_checksum),
            split_manifest_checksum=(self.split_manifest_checksum),
            evaluation_score_set_checksum=(self.evaluation_score_set_checksum),
        )

    @classmethod
    def from_score_manifest(
        cls,
        state: TemporalState,
        manifest: ScoreArtifactManifest,
    ) -> "TemporalDeploymentProvenance":
        calibration_role, evaluation_role = _expected_partition_roles(state)
        calibration_records = manifest.records_for(calibration_role)
        evaluation_records = manifest.records_for(evaluation_role)
        if not calibration_records or not evaluation_records:
            raise ScientificContractError(
                "temporal provenance requires non-empty calibration and evaluation score sets",
                subject=state,
            )

        return cls(
            state=state,
            split_protocol=manifest.coordinate.split_protocol,
            calibration_role=calibration_role,
            evaluation_role=evaluation_role,
            coordinate_checksum=_coordinate_checksum(manifest.coordinate),
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=(manifest.preprocessing_state_set_checksum),
            split_manifest_checksum=(manifest.split_manifest_checksum),
            calibration_score_set_checksum=(_score_set_checksum(calibration_records)),
            evaluation_score_set_checksum=(_score_set_checksum(evaluation_records)),
        )

    def validate_score_manifest(
        self,
        manifest: ScoreArtifactManifest,
    ) -> None:
        observed = TemporalDeploymentProvenance.from_score_manifest(self.state, manifest)
        if observed != self:
            raise ScientificContractError(
                "temporal deployment provenance does not match immutable score artifacts",
                subject=self.state,
                reason=("calibration, evaluation, model, preprocessing, or split evidence changed"),
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


def decide_temporal(
    result: TemporalRecoveryResult,
) -> ScientificDecisionResult:
    if result.recovery_ratio is None:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=result.reason,
        )

    if result.recovered_amount.value > 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.SUPPORTED,
            point_estimate=result.recovery_ratio,
            interval=None,
            rationale=("temporal degradation has positive one-shot recalibration recovery"),
        )

    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=ScientificDecision.BOUNDARY_RESULT,
        point_estimate=result.recovery_ratio,
        interval=None,
        rationale=("temporal degradation has no positive one-shot recalibration recovery"),
    )


def _expected_partition_roles(
    state: TemporalState,
) -> tuple[PartitionRole, PartitionRole]:
    match state:
        case TemporalState.STATIC_REFERENCE | TemporalState.FROZEN_FUTURE:
            return (
                PartitionRole.CALIBRATION,
                PartitionRole.EVALUATION,
            )
        case TemporalState.RECALIBRATED_FUTURE:
            return (
                PartitionRole.FUTURE_RECALIBRATION,
                PartitionRole.EVALUATION,
            )

    raise ValueError(f"unsupported temporal state: {state}")


def _score_set_checksum(
    records: tuple[ScoreRecord, ...],
) -> Checksum:
    entries = sorted(f"{record.scored_client.client_id}:{record.checksum.value}" for record in records)
    return checksum_text("|".join(entries))


def _coordinate_checksum(coordinate: object) -> Checksum:
    payload = json.dumps(
        _canonical_value(coordinate),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return checksum_text(payload)


def _canonical_value(value: object) -> object:
    if isinstance(value, Enum):
        return _canonical_value(value.value)

    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical_value(getattr(value, field.name)) for field in fields(value)}

    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, tuple | list):
        return [_canonical_value(item) for item in value]

    if value is None or isinstance(value, str | int | bool):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical scientific provenance cannot contain non-finite floats")
        return value

    wrapped = getattr(value, "value", None)
    if wrapped is not None and wrapped is not value:
        return _canonical_value(wrapped)

    raise TypeError(f"unsupported canonical provenance value: {type(value).__qualname__}")
