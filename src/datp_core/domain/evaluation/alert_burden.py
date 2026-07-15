from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from datp_core.domain.artifacts.references import CalibrationScoreArtifactId, StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.thresholding.policies import canonical_decimal


class TrafficRateUnit(StrEnum):
    EVENTS_PER_SECOND = "events_per_second"
    EVENTS_PER_MINUTE = "events_per_minute"
    EVENTS_PER_HOUR = "events_per_hour"
    EVENTS_PER_DAY = "events_per_day"


class TrafficRateEvidenceKind(StrEnum):
    MEASURED = "measured"
    CITED = "cited"


class CostDerivationKind(StrEnum):
    MEASURED = "measured"
    ESTIMATED = "estimated"


def _validated_integer_at_least(*, value: object, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainValidationError(detail=f"{name} must be an integer", value=repr(value), constraint="integer")
    if value < minimum:
        raise DomainValidationError(
            detail=f"{name} must be an integer greater than or equal to {minimum}",
            value=repr(value),
            constraint=f"integer >= {minimum}",
        )


def _validated_positive_resample_count(value: object) -> None:
    _validated_integer_at_least(value=value, name="bootstrap resample count", minimum=1)


def _validated_traffic_rate_unit(value: object) -> None:
    if not isinstance(value, TrafficRateUnit):
        raise DomainValidationError(
            detail="traffic rate must use a supported unit",
            value=repr(value),
            constraint="TrafficRateUnit",
        )


def _validated_calibration_count_reference(
    *,
    calibration_artifact_id: object,
    client_id: object,
    recorded_count: object,
) -> None:
    if not isinstance(calibration_artifact_id, CalibrationScoreArtifactId):
        raise DomainValidationError(
            detail="calibration sample count reference requires a calibration artifact id",
            value=repr(calibration_artifact_id),
            constraint="CalibrationScoreArtifactId",
        )
    if not isinstance(client_id, ClientId):
        raise DomainValidationError(
            detail="calibration sample count reference requires a client id",
            value=repr(client_id),
            constraint="ClientId",
        )
    if not isinstance(recorded_count, CalibrationSampleCount):
        raise DomainValidationError(
            detail="calibration sample count reference requires a calibration sample count",
            value=repr(recorded_count),
            constraint="CalibrationSampleCount",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BootstrapResampleCount:
    value: int

    def __post_init__(self) -> None:
        _validated_positive_resample_count(self.value)


@dataclass(frozen=True, slots=True, kw_only=True)
class TrafficRate:
    value: Decimal
    unit: TrafficRateUnit

    def __post_init__(self) -> None:
        canonical_value = canonical_decimal(self.value)
        if canonical_value <= Decimal(0):
            raise DomainValidationError(
                detail="traffic rate must be strictly positive",
                value=str(canonical_value),
                constraint="traffic rate > 0",
            )
        _validated_traffic_rate_unit(self.unit)
        object.__setattr__(self, "value", canonical_value)


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleCount:
    value: int

    def __post_init__(self) -> None:
        _validated_integer_at_least(value=self.value, name="sample count", minimum=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfusionCount:
    value: int

    def __post_init__(self) -> None:
        _validated_integer_at_least(value=self.value, name="confusion count", minimum=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSampleCount:
    value: int

    def __post_init__(self) -> None:
        _validated_integer_at_least(value=self.value, name="calibration sample count", minimum=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSampleCountRef:
    calibration_artifact_id: CalibrationScoreArtifactId
    client_id: ClientId
    recorded_count: CalibrationSampleCount

    def __post_init__(self) -> None:
        _validated_calibration_count_reference(
            calibration_artifact_id=self.calibration_artifact_id,
            client_id=self.client_id,
            recorded_count=self.recorded_count,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MeasuredTrafficRateEvidence:
    traffic_rate: TrafficRate
    scope_identity: StageFingerprint
    measurement_provenance: str
    applicability_period: str

    def __post_init__(self) -> None:
        _validated_traffic_evidence(
            traffic_rate=self.traffic_rate,
            scope_identity=self.scope_identity,
            reference=self.measurement_provenance,
            applicability_period=self.applicability_period,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CitedTrafficRateEvidence:
    traffic_rate: TrafficRate
    scope_identity: StageFingerprint
    source_reference: str
    applicability_period: str

    def __post_init__(self) -> None:
        _validated_traffic_evidence(
            traffic_rate=self.traffic_rate,
            scope_identity=self.scope_identity,
            reference=self.source_reference,
            applicability_period=self.applicability_period,
        )


type TrafficRateEvidence = MeasuredTrafficRateEvidence | CitedTrafficRateEvidence


def _validated_traffic_evidence(
    *, traffic_rate: object, scope_identity: object, reference: object, applicability_period: object
) -> None:
    if not _is_valid_traffic_evidence(traffic_rate, scope_identity, reference, applicability_period):
        raise DomainValidationError(
            detail="traffic evidence requires a typed positive rate, scope, source, and applicability period",
            value=repr((traffic_rate, scope_identity, reference, applicability_period)),
            constraint="TrafficRate, StageFingerprint, and non-empty source/period",
        )


def _is_valid_traffic_evidence(
    traffic_rate: object,
    scope_identity: object,
    reference: object,
    applicability_period: object,
) -> bool:
    return all(
        (
            type(traffic_rate) is TrafficRate,
            type(scope_identity) is StageFingerprint,
            _is_non_empty_string(reference),
            _is_non_empty_string(applicability_period),
        )
    )


def _is_non_empty_string(value: object) -> bool:
    return type(value) is str and bool(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertBurdenResult:
    traffic_evidence: TrafficRateEvidence
    alert_count: ConfusionCount
    applicability_period: str
    evaluation_identity: StageFingerprint

    def __post_init__(self) -> None:
        if not _is_valid_alert_burden_result(self):
            raise DomainValidationError(
                detail="alert burden requires measured or cited traffic-rate evidence and typed evaluation identity",
                value=repr(self),
                constraint="TrafficRateEvidence, ConfusionCount, period, and StageFingerprint",
            )


def _is_valid_alert_burden_result(result: AlertBurdenResult) -> bool:
    return all(
        (
            type(result.traffic_evidence) in {MeasuredTrafficRateEvidence, CitedTrafficRateEvidence},
            type(result.alert_count) is ConfusionCount,
            _is_non_empty_string(result.applicability_period),
            type(result.evaluation_identity) is StageFingerprint,
        )
    )
