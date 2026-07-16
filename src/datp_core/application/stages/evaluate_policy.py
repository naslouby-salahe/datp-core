from dataclasses import dataclass

from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedEvaluationIdentity,
)
from datp_core.domain.artifacts.references import CalibrationScoreArtifactId, StageFingerprint
from datp_core.domain.errors import EvaluationError
from datp_core.domain.evaluation.alert_burden import (
    CalibrationSampleCount,
    CalibrationSampleCountRef,
    ConfusionCount,
    SampleCount,
)
from datp_core.domain.evaluation.operating_points import (
    BalancedAccuracyScore,
    CentralizedPolicyEvaluationResult,
    ClientEligibilityReason,
    ClientEligibilityStatus,
    ClientEvaluationResult,
    ClusterDispersionResult,
    EligibilityCoverageResult,
    EligibleClientSet,
    F1Score,
    FleetDetectionResult,
    FleetDispersionResult,
    FleetEquityResult,
    PolicyEvaluationResult,
    PrecisionScore,
    RecallScore,
    TemporalPolicyEvaluationResult,
    ZeroDenominatorPolicy,
    cv_outcome,
)
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ClaimOutcome,
    EligibilityCoverage,
    FalsePositiveRate,
    TruePositiveRate,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CentralizedClientTestScoreArtifact,
    ClientEvaluationMap,
    ClientTestScoreArtifact,
    TemporalScoreArtifactSet,
    TestScoreArtifactSet,
)
from datp_core.domain.mathematics.quantiles import nearest_rank_value
from datp_core.domain.thresholding.federated_statistics import ThresholdComparatorRole
from datp_core.domain.thresholding.policies import (
    CentralizedThresholdAssignment,
    CoreThresholdPolicy,
    ThresholdAssignment,
    ThresholdValue,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientConfusionEvidence:
    true_positive: ConfusionCount
    false_positive: ConfusionCount
    true_negative: ConfusionCount
    false_negative: ConfusionCount
    calibration_sample_count: CalibrationSampleCount


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluatePolicyRequest:
    policy: CoreThresholdPolicy
    evaluation_identity: StageFingerprint
    score_set: TestScoreArtifactSet
    assignment: ThresholdAssignment
    eligible_client_set: EligibleClientSet
    confusion_evidence: ClientEvaluationMap[ClientConfusionEvidence]
    auroc_control: AuRocScore
    zero_mean_cv_wording_outcome: ClaimOutcome
    cluster_dispersion: ClusterDispersionResult | None


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateTemporalPolicyRequest:
    policy: CoreThresholdPolicy
    evaluation_identity: StageFingerprint
    score_set: TemporalScoreArtifactSet
    assignment: ThresholdAssignment
    eligible_client_set: EligibleClientSet
    confusion_evidence: ClientEvaluationMap[ClientConfusionEvidence]
    auroc_control: AuRocScore
    zero_mean_cv_wording_outcome: ClaimOutcome
    cluster_dispersion: ClusterDispersionResult | None
    assignment_identity: StageFingerprint


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedPolicyRequest:
    policy: ThresholdComparatorRole
    evaluation_identity: CentralizedEvaluationIdentity
    score_artifacts: tuple[CentralizedClientTestScoreArtifact, ...]
    assignment: CentralizedThresholdAssignment
    eligible_client_set: EligibleClientSet
    confusion_evidence: ClientEvaluationMap[ClientConfusionEvidence]
    auroc_control: AuRocScore
    zero_mean_cv_wording_outcome: ClaimOutcome
    cluster_dispersion: ClusterDispersionResult | None


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationInputs:
    policy: CoreThresholdPolicy
    evaluation_identity: StageFingerprint
    score_roster: tuple[ClientId, ...]
    score_artifacts: tuple[ClientTestScoreArtifact, ...]
    assignment: ThresholdAssignment
    eligible_client_set: EligibleClientSet
    confusion_evidence: ClientEvaluationMap[ClientConfusionEvidence]
    auroc_control: AuRocScore
    zero_mean_cv_wording_outcome: ClaimOutcome
    cluster_dispersion: ClusterDispersionResult | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientEvaluationInputs:
    client_id: ClientId
    score_artifact: ClientTestScoreArtifact
    threshold: ThresholdValue
    evidence: ClientConfusionEvidence
    assignment: ThresholdAssignment
    eligible_client_set: EligibleClientSet


class PolicyEvaluator:
    def evaluate(self, request: EvaluatePolicyRequest) -> PolicyEvaluationResult:
        if type(request.score_set) is not TestScoreArtifactSet:
            _raise_invalid_score_set(score_set=request.score_set, required_role="test")
        score_values = tuple(entry.value for entry in request.score_set.per_client.values.entries)
        return _evaluate_policy(
            EvaluationInputs(
                policy=request.policy,
                evaluation_identity=request.evaluation_identity,
                score_roster=request.score_set.per_client.values.roster.client_ids,
                score_artifacts=score_values,
                assignment=request.assignment,
                eligible_client_set=request.eligible_client_set,
                confusion_evidence=request.confusion_evidence,
                auroc_control=request.auroc_control,
                zero_mean_cv_wording_outcome=request.zero_mean_cv_wording_outcome,
                cluster_dispersion=request.cluster_dispersion,
            )
        )

    def evaluate_temporal(self, request: EvaluateTemporalPolicyRequest) -> TemporalPolicyEvaluationResult:
        if type(request.score_set) is not TemporalScoreArtifactSet:
            _raise_invalid_score_set(score_set=request.score_set, required_role="temporal")
        temporal_artifacts = tuple(entry.value for entry in request.score_set.per_client.values.entries)
        result = _evaluate_policy(
            EvaluationInputs(
                policy=request.policy,
                evaluation_identity=request.evaluation_identity,
                score_roster=request.score_set.per_client.values.roster.client_ids,
                score_artifacts=tuple(artifact.test_artifact for artifact in temporal_artifacts),
                assignment=request.assignment,
                eligible_client_set=request.eligible_client_set,
                confusion_evidence=request.confusion_evidence,
                auroc_control=request.auroc_control,
                zero_mean_cv_wording_outcome=request.zero_mean_cv_wording_outcome,
                cluster_dispersion=request.cluster_dispersion,
            )
        )
        return TemporalPolicyEvaluationResult(
            temporal_score_identity=request.score_set.lineage.scoring_identity.value,
            temporal_window_identity=request.score_set.window_identity.value,
            assignment_identity=request.assignment_identity,
            policy_evaluation=result,
        )

    def evaluate_centralized(self, request: EvaluateCentralizedPolicyRequest) -> CentralizedPolicyEvaluationResult:
        return _evaluate_centralized_policy(request)


def _evaluate_policy(inputs: EvaluationInputs) -> PolicyEvaluationResult:
    _validate_evaluation_inputs(inputs)
    client_results = tuple(
        _client_result(
            ClientEvaluationInputs(
                client_id=score_artifact.client_id,
                score_artifact=score_artifact,
                threshold=assignment_entry.value,
                evidence=evidence_entry.value,
                assignment=inputs.assignment,
                eligible_client_set=inputs.eligible_client_set,
            )
        )
        for score_artifact, assignment_entry, evidence_entry in zip(
            inputs.score_artifacts,
            inputs.assignment.per_client_tau.values.entries,
            inputs.confusion_evidence.values.entries,
            strict=True,
        )
    )
    return PolicyEvaluationResult(
        policy=inputs.policy,
        evaluation_identity=inputs.evaluation_identity,
        eligible_client_set=inputs.eligible_client_set,
        client_results=client_results,
        fleet_dispersion=_fleet_dispersion(
            client_results=client_results,
            eligible_client_set=inputs.eligible_client_set,
            zero_mean_cv_wording_outcome=inputs.zero_mean_cv_wording_outcome,
        ),
        fleet_detection=_fleet_detection(client_results=client_results, auroc_control=inputs.auroc_control),
        fleet_equity=_fleet_equity(client_results=client_results),
        cluster_dispersion=inputs.cluster_dispersion,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedClientEvaluationInputs:
    client_id: ClientId
    score_artifact: CentralizedClientTestScoreArtifact
    threshold: ThresholdValue
    evidence: ClientConfusionEvidence
    assignment: CentralizedThresholdAssignment
    eligible_client_set: EligibleClientSet


def _evaluate_centralized_policy(
    request: EvaluateCentralizedPolicyRequest,
) -> CentralizedPolicyEvaluationResult:
    _validate_centralized_evaluation_inputs(request)
    results: list[ClientEvaluationResult] = []
    for score_artifact, evidence_entry in zip(
        request.score_artifacts,
        request.confusion_evidence.values.entries,
        strict=True,
    ):
        results.append(
            _centralized_client_result(
                CentralizedClientEvaluationInputs(
                    client_id=score_artifact.client_id,
                    score_artifact=score_artifact,
                    threshold=request.assignment.tau,
                    evidence=evidence_entry.value,
                    assignment=request.assignment,
                    eligible_client_set=request.eligible_client_set,
                )
            )
        )
    client_results = tuple(results)
    return CentralizedPolicyEvaluationResult(
        policy=request.policy,
        evaluation_identity=request.evaluation_identity,
        eligible_client_set=request.eligible_client_set,
        client_results=client_results,
        fleet_dispersion=_fleet_dispersion(
            client_results=client_results,
            eligible_client_set=request.eligible_client_set,
            zero_mean_cv_wording_outcome=request.zero_mean_cv_wording_outcome,
        ),
        fleet_detection=_fleet_detection(client_results=client_results, auroc_control=request.auroc_control),
        fleet_equity=_fleet_equity(client_results=client_results),
        cluster_dispersion=request.cluster_dispersion,
    )


def _validate_centralized_evaluation_inputs(request: EvaluateCentralizedPolicyRequest) -> None:
    expected_roster = request.eligible_client_set.roster.client_ids
    score_roster = tuple(artifact.client_id for artifact in request.score_artifacts)
    if not all(
        (
            request.policy is ThresholdComparatorRole.CENTRALIZED_MODEL_B0,
            score_roster == expected_roster,
            type(request.assignment.tau) is ThresholdValue,
            request.confusion_evidence.values.roster.client_ids == expected_roster,
        )
    ):
        raise EvaluationError(
            detail=(
                "centralized policy evaluation requires aligned committed test aggregates, "
                "assignments, and fixed eligibility"
            ),
            metric="policy_evaluation",
            scope="centralized test-score aggregate and eligible-client-set alignment",
        )


def _make_client_result(
    inputs: ClientEvaluationInputs | CentralizedClientEvaluationInputs,
    *,
    calibration_artifact_id: CalibrationScoreArtifactId | CentralizedCalibrationScoringIdentity,
    fallback_fingerprint: StageFingerprint,
) -> ClientEvaluationResult:
    if inputs.score_artifact.client_id != inputs.client_id:
        raise EvaluationError(
            detail="client score aggregate must remain aligned with its client identifier",
            metric="client_evaluation",
            scope="committed test-score aggregate",
        )
    if (
        inputs.evidence.true_negative.value + inputs.evidence.false_positive.value
        != inputs.score_artifact.benign_sample_count.value
        or inputs.evidence.true_positive.value + inputs.evidence.false_negative.value
        != inputs.score_artifact.attack_sample_count.value
    ):
        raise EvaluationError(
            detail="confusion evidence must reconcile with the committed aggregate sample counts",
            metric="confusion_counts",
            scope=inputs.client_id.value,
        )
    status, reason = _eligibility_for(client_id=inputs.client_id, eligible_client_set=inputs.eligible_client_set)
    true_positive_rate = _ratio(inputs.evidence.true_positive.value, inputs.score_artifact.attack_sample_count.value)
    false_positive_rate = _ratio(inputs.evidence.false_positive.value, inputs.score_artifact.benign_sample_count.value)
    precision = _ratio(
        inputs.evidence.true_positive.value, inputs.evidence.true_positive.value + inputs.evidence.false_positive.value
    )
    f1 = _ratio(
        2 * inputs.evidence.true_positive.value,
        2 * inputs.evidence.true_positive.value
        + inputs.evidence.false_positive.value
        + inputs.evidence.false_negative.value,
    )
    return ClientEvaluationResult(
        client_id=inputs.client_id,
        true_positive=inputs.evidence.true_positive,
        false_positive=inputs.evidence.false_positive,
        true_negative=inputs.evidence.true_negative,
        false_negative=inputs.evidence.false_negative,
        benign_test_count=SampleCount(value=inputs.score_artifact.benign_sample_count.value),
        attack_test_count=SampleCount(value=inputs.score_artifact.attack_sample_count.value),
        assigned_threshold=inputs.threshold,
        false_positive_rate=FalsePositiveRate(value=false_positive_rate),
        true_positive_rate=TruePositiveRate(value=true_positive_rate),
        precision=PrecisionScore(value=precision),
        recall=RecallScore(value=true_positive_rate),
        f1=F1Score(value=f1),
        balanced_accuracy=BalancedAccuracyScore(value=(true_positive_rate + (1 - false_positive_rate)) / 2),
        eligibility_status=status,
        eligibility_reason=reason,
        calibration_sample_count_reference=CalibrationSampleCountRef(
            calibration_artifact_id=calibration_artifact_id,
            client_id=inputs.client_id,
            recorded_count=inputs.evidence.calibration_sample_count,
        ),
        eligible_client_set_identity=inputs.eligible_client_set.identity,
        fallback_fingerprint=fallback_fingerprint,
        test_split_identity=inputs.score_artifact.test_split_identity.value,
        zero_denominator_policy=ZeroDenominatorPolicy.ZERO,
    )


def _centralized_client_result(inputs: CentralizedClientEvaluationInputs) -> ClientEvaluationResult:
    return _make_client_result(
        inputs,
        calibration_artifact_id=inputs.assignment.centralized_calibration_score_identity,
        fallback_fingerprint=inputs.assignment.threshold_identity.value,
    )


def _client_result(inputs: ClientEvaluationInputs) -> ClientEvaluationResult:
    return _make_client_result(
        inputs,
        calibration_artifact_id=inputs.assignment.calibration_score_artifact_id,
        fallback_fingerprint=inputs.assignment.fallback_fingerprint,
    )


def _validate_evaluation_inputs(inputs: EvaluationInputs) -> None:
    expected_roster = inputs.eligible_client_set.roster.client_ids
    if not all(
        (
            type(inputs.policy) is CoreThresholdPolicy,
            inputs.score_roster == expected_roster,
            tuple(artifact.client_id for artifact in inputs.score_artifacts) == expected_roster,
            inputs.assignment.policy is inputs.policy,
            inputs.assignment.per_client_tau.values.roster.client_ids == expected_roster,
            inputs.confusion_evidence.values.roster.client_ids == expected_roster,
            inputs.assignment.eligible_client_set_identity == inputs.eligible_client_set.identity,
        )
    ):
        raise EvaluationError(
            detail="policy evaluation requires aligned committed test aggregates, assignments, and fixed eligibility",
            metric="policy_evaluation",
            scope="test-score aggregate and eligible-client-set alignment",
        )


def _eligibility_for(
    *, client_id: ClientId, eligible_client_set: EligibleClientSet
) -> tuple[ClientEligibilityStatus, ClientEligibilityReason]:
    if client_id in eligible_client_set.eligible_clients:
        return ClientEligibilityStatus.ELIGIBLE, ClientEligibilityReason.SUFFICIENT_CALIBRATION
    reason = next(item.reason for item in eligible_client_set.ineligible_reasons if item.client_id == client_id)
    if reason is ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK:
        return ClientEligibilityStatus.FALLBACK_ASSIGNED, reason
    return ClientEligibilityStatus.EXCLUDED, reason


def _fleet_dispersion(
    *,
    client_results: tuple[ClientEvaluationResult, ...],
    eligible_client_set: EligibleClientSet,
    zero_mean_cv_wording_outcome: ClaimOutcome,
) -> FleetDispersionResult:
    eligible_results = tuple(
        result for result in client_results if result.client_id in eligible_client_set.eligible_clients
    )
    fpr_values = tuple(result.false_positive_rate.value for result in eligible_results)
    tpr_values = tuple(result.true_positive_rate.value for result in eligible_results)
    return FleetDispersionResult(
        cv_fpr=cv_outcome(
            values=fpr_values,
            affected_scope_identity=eligible_client_set.identity,
            wording_outcome=zero_mean_cv_wording_outcome,
        ),
        cv_tpr=cv_outcome(
            values=tpr_values,
            affected_scope_identity=eligible_client_set.identity,
            wording_outcome=zero_mean_cv_wording_outcome,
        ),
        iqr_fpr=_interquartile_range(fpr_values),
        fpr_range=max(fpr_values) - min(fpr_values),
        worst_client_fpr=FalsePositiveRate(value=max(fpr_values)),
        eligibility_coverage=EligibilityCoverageResult(
            eligible_count=len(eligible_results),
            roster_count=len(client_results),
            coverage=EligibilityCoverage(value=len(eligible_results) / len(client_results)),
            eligible_client_set_identity=eligible_client_set.identity,
        ),
    )


def _fleet_detection(
    *, client_results: tuple[ClientEvaluationResult, ...], auroc_control: AuRocScore
) -> FleetDetectionResult:
    f1_values = tuple(sorted(result.f1.value for result in client_results))
    return FleetDetectionResult(
        macro_f1=F1Score(value=sum(f1_values) / len(f1_values)),
        p10_macro_f1=F1Score(value=nearest_rank_value(values=f1_values, percentile=0.1)),
        worst_client_balanced_accuracy=BalancedAccuracyScore(
            value=min(result.balanced_accuracy.value for result in client_results)
        ),
        auroc_control=auroc_control,
    )


def _fleet_equity(*, client_results: tuple[ClientEvaluationResult, ...]) -> FleetEquityResult:
    rates = tuple(result.false_positive_rate.value for result in client_results)
    total = sum(rates)
    squared_total = sum(rate**2 for rate in rates)
    jain_index = 1.0 if squared_total == 0 else total**2 / (len(rates) * squared_total)
    return FleetEquityResult(jain_index=jain_index, gini_coefficient=_gini_coefficient(rates))


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _interquartile_range(values: tuple[float, ...]) -> float:
    ordered = tuple(sorted(values))
    midpoint = len(ordered) // 2
    if midpoint == 0:
        return 0.0
    lower = ordered[:midpoint]
    upper = ordered[-midpoint:]
    return sum(upper) / len(upper) - sum(lower) / len(lower)


def _gini_coefficient(values: tuple[float, ...]) -> float:
    total = sum(values)
    if total == 0:
        return 0.0
    ordered = tuple(sorted(values))
    numerator = sum((2 * index - len(ordered) - 1) * value for index, value in enumerate(ordered, start=1))
    return numerator / (len(ordered) * total)


def _raise_invalid_score_set(*, score_set: object, required_role: str) -> None:
    raise EvaluationError(
        detail=f"policy evaluation requires a committed {required_role}-role score aggregate",
        metric="score_set_role",
        scope=type(score_set).__name__,
    )
