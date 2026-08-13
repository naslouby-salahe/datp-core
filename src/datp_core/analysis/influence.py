from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument, FederatedEvaluationRequest
from datp_core.analysis.metrics.federated_execution import prepare_federated_evaluation
from datp_core.analysis.metrics.fixed_score_construction import build_federated_evaluation_inputs
from datp_core.analysis.metrics.models import MetricStatus, PopulationMetricResult, metric_by_id
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import EvidenceRole, FederatedThresholdMethod, MetricId, PartitionRole
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    MetricValue,
    Ratio,
    Seed,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.thresholds.calibration.service import eligible_calibration_scores
from datp_core.thresholds.policies.shared import construct_shared_threshold
from datp_core.thresholds.protocols import SHARED_THRESHOLD_PROTOCOL

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
LODO_HIGH_INFLUENCE_RELATIVE_SHIFT = Ratio(0.25)


class RelativeLodoShiftStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE_NEAR_ZERO_FULL_EFFECT = "unavailable_near_zero_full_effect"


class LodoHighInfluenceTrigger(StrEnum):
    NONPOSITIVE_OMISSION = "nonpositive_omission"
    RELATIVE_SHIFT = "relative_shift"


@dataclass(frozen=True, slots=True)
class LeaveOneDeviceEffect:
    seed: Seed
    omitted_device: ClientIdentity
    shared_threshold: ThresholdValue
    shared_cv_fpr: MetricValue
    local_cv_fpr: MetricValue

    @property
    def delta(self) -> MetricValue:
        return MetricValue(self.shared_cv_fpr.value - self.local_cv_fpr.value)


class LeaveOneDeviceSummary(StrictModel):
    omitted_device: ClientIdentity
    seed_deltas: tuple[MetricValue, ...]
    mean_delta: MetricValue


class LeaveOneDeviceOutDiagnostics(StrictModel):
    device_summaries: tuple[LeaveOneDeviceSummary, ...]
    full_mean_delta: MetricValue
    minimum_lodo_mean: MetricValue
    maximum_lodo_mean: MetricValue
    maximum_lodo_shift: MetricValue
    positive_direction_retention: Ratio
    nonpositive_omissions: tuple[ClientIdentity, ...]
    relative_maximum_lodo_shift: MetricValue | None
    relative_shift_status: RelativeLodoShiftStatus
    high_influence_triggers: tuple[LodoHighInfluenceTrigger, ...]
    high_influence: bool

    @model_validator(mode="after")
    def validate_relative_shift(self) -> "LeaveOneDeviceOutDiagnostics":
        relative_available = self.relative_shift_status is RelativeLodoShiftStatus.AVAILABLE
        if relative_available != (self.relative_maximum_lodo_shift is not None):
            raise ValueError("relative LODO shift availability must match its status")
        if tuple(sorted(self.nonpositive_omissions)) != self.nonpositive_omissions:
            raise ValueError("nonpositive LODO omissions must be sorted")
        if tuple(sorted(self.device_summaries, key=lambda item: item.omitted_device)) != self.device_summaries:
            raise ValueError("LODO device summaries must be sorted")
        means = tuple(summary.mean_delta.value for summary in self.device_summaries)
        if self.minimum_lodo_mean.value != min(means) or self.maximum_lodo_mean.value != max(means):
            raise ValueError("LODO extrema must match the retained device means")
        expected_shift = max(abs(mean - self.full_mean_delta.value) for mean in means)
        if self.maximum_lodo_shift.value != expected_shift:
            raise ValueError("maximum LODO shift must match the retained device means and full mean")
        expected_relative = (
            None
            if abs(self.full_mean_delta.value) <= NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value
            else self.maximum_lodo_shift.value / abs(self.full_mean_delta.value)
        )
        if expected_relative is None:
            if self.relative_shift_status is not RelativeLodoShiftStatus.UNAVAILABLE_NEAR_ZERO_FULL_EFFECT:
                raise ValueError("near-zero full effect requires unavailable relative LODO shift")
        elif self.relative_maximum_lodo_shift is None or self.relative_maximum_lodo_shift.value != expected_relative:
            raise ValueError("relative LODO shift must match the full effect and maximum shift")
        expected_triggers: list[LodoHighInfluenceTrigger] = []
        if self.nonpositive_omissions:
            expected_triggers.append(LodoHighInfluenceTrigger.NONPOSITIVE_OMISSION)
        if expected_relative is not None and expected_relative >= LODO_HIGH_INFLUENCE_RELATIVE_SHIFT.value:
            expected_triggers.append(LodoHighInfluenceTrigger.RELATIVE_SHIFT)
        if self.high_influence_triggers != tuple(expected_triggers):
            raise ValueError("LODO high-influence triggers must match the retained sensitivity evidence")
        if self.high_influence != bool(expected_triggers):
            raise ValueError("LODO high-influence flag must match its triggers")
        return self


def leave_one_device_out_effects(
    *,
    shared: FederatedEvaluationDocument,
    local: FederatedEvaluationDocument,
) -> tuple[LeaveOneDeviceEffect, ...]:
    _validate_confirmatory_pair(shared, local)
    manifest = shared.fixed_score_evidence.score_manifest
    if len(manifest.evaluation_records) != 9:
        raise ScientificContractError(ErrorMessage("confirmatory leave-one-device-out requires exactly nine devices"))
    local_by_client = {item.client: item for item in local.clients}
    if len(local_by_client) != len(manifest.evaluation_records):
        raise ScientificContractError(
            ErrorMessage("local evaluation must contain exactly one result per fixed-score client")
        )
    effects: list[LeaveOneDeviceEffect] = []
    for omitted in sorted(record.scored_client for record in manifest.evaluation_records):
        reduced = _without_client(manifest, omitted)
        inputs = build_federated_evaluation_inputs(reduced, FederatedThresholdMethod.SHARED_THRESHOLD)
        calibration = eligible_calibration_scores(reduced, PartitionRole.CALIBRATION)
        threshold = construct_shared_threshold(
            calibration,
            SHARED_THRESHOLD_PROTOCOL,
        )
        shared_publication = prepare_federated_evaluation(
            FederatedEvaluationRequest(
                execution_key=shared.execution_key,
                score_manifest=reduced,
                threshold_result=threshold,
                cohort=inputs.cohort,
                fixed_score_evidence=inputs.fixed_score_evidence,
                evidence_role=EvidenceRole.CONFIRMATORY,
                calibration_scores=calibration,
                target_quantile=threshold.quantile,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                temporal_provenance=None,
                temporal_threshold_provenance=None,
                execution_identity=None,
            )
        )
        retained_local_clients = tuple(
            local_by_client[record.scored_client]
            for record in reduced.evaluation_records
            if record.scored_client in local_by_client
        )
        if len(retained_local_clients) != len(reduced.evaluation_records):
            raise ScientificContractError(ErrorMessage("local evaluation must retain every non-omitted client"))
        local_population = calculate_population_metrics(retained_local_clients, cohort=inputs.cohort)
        effects.append(
            LeaveOneDeviceEffect(
                seed=shared.score_coordinate.training_seed,
                omitted_device=omitted,
                shared_threshold=threshold.shared_threshold,
                shared_cv_fpr=_population_metric(shared_publication.artifacts.population),
                local_cv_fpr=_population_metric(local_population),
            )
        )
    return tuple(effects)


def summarize_leave_one_device_out_effects(
    effects: tuple[LeaveOneDeviceEffect, ...],
    *,
    full_mean_delta: MetricValue,
    required_seed_count: int,
) -> LeaveOneDeviceOutDiagnostics:
    if required_seed_count < 1:
        raise ValueError("leave-one-device-out requires a positive seed count")
    grouped: dict[ClientIdentity, list[LeaveOneDeviceEffect]] = {}
    for effect in effects:
        grouped.setdefault(effect.omitted_device, []).append(effect)
    summaries: list[LeaveOneDeviceSummary] = []
    for device, device_effects in sorted(grouped.items()):
        seeds = tuple(effect.seed for effect in device_effects)
        if len(seeds) != required_seed_count or len(set(seeds)) != required_seed_count:
            raise ScientificContractError(ErrorMessage("every omitted device requires every confirmatory seed"))
        deltas = tuple(effect.delta for effect in sorted(device_effects, key=lambda item: item.seed))
        summaries.append(
            LeaveOneDeviceSummary(
                omitted_device=device,
                seed_deltas=deltas,
                mean_delta=MetricValue(sum(delta.value for delta in deltas) / len(deltas)),
            )
        )
    if not summaries:
        raise ScientificContractError(ErrorMessage("leave-one-device-out requires at least one omitted device"))
    means = tuple(summary.mean_delta.value for summary in summaries)
    maximum_shift = MetricValue(max(abs(mean - full_mean_delta.value) for mean in means))
    nonpositive = tuple(summary.omitted_device for summary in summaries if summary.mean_delta.value <= 0.0)
    if abs(full_mean_delta.value) <= NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value:
        relative_status = RelativeLodoShiftStatus.UNAVAILABLE_NEAR_ZERO_FULL_EFFECT
        relative_shift = None
    else:
        relative_status = RelativeLodoShiftStatus.AVAILABLE
        relative_shift = MetricValue(maximum_shift.value / abs(full_mean_delta.value))
    triggers: list[LodoHighInfluenceTrigger] = []
    if nonpositive:
        triggers.append(LodoHighInfluenceTrigger.NONPOSITIVE_OMISSION)
    if relative_shift is not None and relative_shift.value >= LODO_HIGH_INFLUENCE_RELATIVE_SHIFT.value:
        triggers.append(LodoHighInfluenceTrigger.RELATIVE_SHIFT)
    return LeaveOneDeviceOutDiagnostics(
        device_summaries=tuple(summaries),
        full_mean_delta=full_mean_delta,
        minimum_lodo_mean=MetricValue(min(means)),
        maximum_lodo_mean=MetricValue(max(means)),
        maximum_lodo_shift=maximum_shift,
        positive_direction_retention=Ratio(
            sum(summary.mean_delta.value > 0.0 for summary in summaries) / len(summaries)
        ),
        nonpositive_omissions=nonpositive,
        relative_maximum_lodo_shift=relative_shift,
        relative_shift_status=relative_status,
        high_influence_triggers=tuple(triggers),
        high_influence=bool(triggers),
    )


def _without_client(
    manifest: FederatedScoreArtifactManifest,
    omitted: ClientIdentity,
) -> FederatedScoreArtifactManifest:
    calibration_records = tuple(record for record in manifest.calibration_records if record.scored_client != omitted)
    evaluation_records = tuple(record for record in manifest.evaluation_records if record.scored_client != omitted)
    if len(calibration_records) != len(manifest.calibration_records) - 1:
        raise ScientificContractError(ErrorMessage("omitted device must have one calibration score record"))
    if len(evaluation_records) != len(manifest.evaluation_records) - 1:
        raise ScientificContractError(ErrorMessage("omitted device must have one evaluation score record"))
    return ScoreArtifactManifest(
        coordinate=manifest.coordinate,
        scored_split_protocol=manifest.scored_split_protocol,
        calibration_records=calibration_records,
        evaluation_records=evaluation_records,
    )


def _population_metric(population: PopulationMetricResult) -> MetricValue:
    metric = metric_by_id(population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    if metric.status is not MetricStatus.AVAILABLE or metric.value is None:
        raise ScientificContractError(ErrorMessage("leave-one-device-out CV(FPR) must be available"))
    return metric.value


def _validate_confirmatory_pair(shared: FederatedEvaluationDocument, local: FederatedEvaluationDocument) -> None:
    if shared.threshold_method is not FederatedThresholdMethod.SHARED_THRESHOLD:
        raise ScientificContractError(ErrorMessage("leave-one-device-out requires the shared threshold evaluation"))
    if local.threshold_method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
        raise ScientificContractError(ErrorMessage("leave-one-device-out requires the local threshold evaluation"))
    if shared.evidence_role is not EvidenceRole.CONFIRMATORY or local.evidence_role is not EvidenceRole.CONFIRMATORY:
        raise ScientificContractError(ErrorMessage("leave-one-device-out is restricted to confirmatory evidence"))
    if shared.fixed_score_evidence.score_manifest != local.fixed_score_evidence.score_manifest:
        raise ScientificContractError(ErrorMessage("leave-one-device-out requires one shared fixed score manifest"))
