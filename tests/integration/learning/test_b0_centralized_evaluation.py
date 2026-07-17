from math import isclose

from datp_core.application.stages.evaluate_policy import (
    ClientConfusionEvidence,
    EvaluateCentralizedPolicyRequest,
    PolicyEvaluator,
)
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    StageFingerprint,
)
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.evaluation.alert_burden import (
    CalibrationSampleCount,
    ConfusionCount,
)
from datp_core.domain.evaluation.operating_points import (
    ClientEligibilityStatus,
    EligibleClientSet,
    ValidCvResult,
)
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ClaimOutcome,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CentralizedClientTestScoreArtifact,
    ClientEvaluationMap,
    ClientMap,
    ClientMapEntry,
    ClientRoster,
    ScoreSampleCount,
)
from datp_core.domain.runtime.admissibility import BatchSize
from datp_core.domain.thresholding.federated_statistics import ThresholdComparatorRole
from datp_core.domain.thresholding.policies import (
    CentralizedThresholdAssignment,
    ThresholdValue,
)


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _evaluation_identity() -> CentralizedEvaluationIdentity:
    return CentralizedEvaluationIdentity(value=_fingerprint("1"))


def _test_artifact(*, client_id: ClientId, character: str) -> CentralizedClientTestScoreArtifact:
    score_ref = ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=ArtifactType.TEST_SCORE_SET,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )
    return CentralizedClientTestScoreArtifact(
        client_id=client_id,
        test_split_identity=SplitIdentity(value=_fingerprint("a")),
        split_manifest_hash="b" * 64,
        test_scoring_identity=CentralizedTestScoringIdentity(value=_fingerprint("c")),
        centralized_checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("d")),
        centralized_checkpoint_content_hash="e" * 64,
        scoring_batch_size=BatchSize(value=4),
        benign_scores_ref=score_ref,
        benign_sample_count=ScoreSampleCount(value=10),
        benign_content_hash=character * 64,
        benign_row_order_checksum="benign_checksum",
        attack_scores_ref=score_ref,
        attack_sample_count=ScoreSampleCount(value=10),
        attack_content_hash=character * 64,
        attack_row_order_checksum="attack_checksum",
        aggregate_manifest_hash=character * 64,
        score_schema_version=ArtifactSchemaVersion(value="v1"),
    )


def test_evaluate_centralized_policy_computes_correct_confusion_and_fleet_metrics() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    roster = ClientRoster(client_ids=(client_a, client_b))

    score_a = _test_artifact(client_id=client_a, character="2")
    score_b = _test_artifact(client_id=client_b, character="3")

    assignment = CentralizedThresholdAssignment(
        tau=ThresholdValue(value=1.5),
        centralized_calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("4")),
        threshold_identity=CentralizedThresholdIdentity(value=_fingerprint("5")),
    )

    eligible_set = EligibleClientSet(
        roster=roster,
        protocol_eligibility_rule_identity=_fingerprint("e"),
        eligible_clients=(client_a, client_b),
        ineligible_reasons=(),
        identity=_fingerprint("f"),
    )

    evidence_a = ClientConfusionEvidence(
        true_positive=ConfusionCount(value=8),
        false_positive=ConfusionCount(value=2),
        true_negative=ConfusionCount(value=8),
        false_negative=ConfusionCount(value=2),
        calibration_sample_count=CalibrationSampleCount(value=50),
    )
    evidence_b = ClientConfusionEvidence(
        true_positive=ConfusionCount(value=9),
        false_positive=ConfusionCount(value=1),
        true_negative=ConfusionCount(value=9),
        false_negative=ConfusionCount(value=1),
        calibration_sample_count=CalibrationSampleCount(value=60),
    )

    confusion_map = ClientEvaluationMap(
        values=ClientMap(
            roster=roster,
            entries=(
                ClientMapEntry(client_id=client_a, value=evidence_a),
                ClientMapEntry(client_id=client_b, value=evidence_b),
            ),
        )
    )

    request = EvaluateCentralizedPolicyRequest(
        policy=ThresholdComparatorRole.CENTRALIZED_MODEL_B0,
        evaluation_identity=_evaluation_identity(),
        score_artifacts=(score_a, score_b),
        assignment=assignment,
        eligible_client_set=eligible_set,
        confusion_evidence=confusion_map,
        auroc_control=AuRocScore(value=0.9),
        zero_mean_cv_wording_outcome=ClaimOutcome.WEAK_POSITIVE,
        cluster_dispersion=None,
    )

    evaluator = PolicyEvaluator()
    result = evaluator.evaluate_centralized(request)

    assert result.policy is ThresholdComparatorRole.CENTRALIZED_MODEL_B0
    assert result.evaluation_identity == request.evaluation_identity
    assert len(result.client_results) == 2

    client_res_a = result.client_results[0]
    assert client_res_a.client_id == client_a
    assert client_res_a.true_positive.value == 8
    assert client_res_a.false_positive.value == 2
    assert client_res_a.true_negative.value == 8
    assert client_res_a.false_negative.value == 2
    assert client_res_a.assigned_threshold.value == 1.5
    assert client_res_a.eligibility_status is ClientEligibilityStatus.ELIGIBLE

    # Fleet dispersion point estimates (Coefficient of Variation)
    assert isinstance(result.fleet_dispersion.cv_fpr, ValidCvResult)
    assert isinstance(result.fleet_dispersion.cv_tpr, ValidCvResult)
    assert isclose(result.fleet_dispersion.cv_fpr.point_estimate, 1 / 3)
    assert isclose(result.fleet_dispersion.cv_tpr.point_estimate, 1 / 17)
