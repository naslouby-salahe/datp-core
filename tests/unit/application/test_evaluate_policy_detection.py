import pytest

from datp_core.application.stages.evaluate_policy import (
    ClientConfusionEvidence,
    EvaluatePolicyRequest,
    PolicyEvaluator,
)
from datp_core.domain.artifacts import lineage as artifact_lineage
from datp_core.domain.artifacts import references as artifact_references
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CheckpointIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    SplitIdentity,
    ThresholdIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount, ConfusionCount
from datp_core.domain.evaluation.operating_points import EligibleClientSet
from datp_core.domain.evaluation.statistical_results import AuRocScore, ClaimOutcome
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning import scores as learning_scores
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactId,
    ClientEvaluationMap,
    ClientMap,
    ClientMapEntry,
    ClientRoster,
    ScoreSampleCount,
    ThresholdAssignmentSet,
)
from datp_core.domain.thresholding.policies import CoreThresholdPolicy, ThresholdAssignment, ThresholdValue
from tests.support.score_artifacts import ScoreLineageContextRequest, score_lineage_context

# Client A: perfect (F1=1.0, BA=1.0); B: moderate (F1=0.8, BA=0.8); C: poor (F1=0.5, BA=0.5).
_CONFUSION_BY_LETTER = {"a": (10, 0, 10, 0), "b": (8, 2, 8, 2), "c": (5, 5, 5, 5)}
_BENIGN_CHARACTERS = {"a": "1", "b": "2", "c": "3"}
_ATTACK_CHARACTERS = {"a": "4", "b": "5", "c": "6"}


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _artifact_ref(*, character: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


type _ScoreLineage = tuple[
    SplitIdentity,
    CheckpointIdentity,
    FittedPreprocessorIdentity,
    FeatureSchemaIdentity,
    artifact_lineage.TestScoringIdentity,
]


def _score_entry(
    *, letter: str, client: ClientId, lineage: _ScoreLineage
) -> ClientMapEntry[learning_scores.ClientTestScoreArtifact]:
    split_identity, checkpoint_identity, preprocessor_identity, schema_identity, test_scoring_identity = lineage
    benign_character = _BENIGN_CHARACTERS[letter]
    attack_character = _ATTACK_CHARACTERS[letter]
    true_positive, false_positive, true_negative, false_negative = _CONFUSION_BY_LETTER[letter]
    return ClientMapEntry(
        client_id=client,
        value=learning_scores.ClientTestScoreArtifact(
            client_id=client,
            test_split_identity=split_identity,
            split_manifest_hash="3" * 64,
            test_scoring_identity=test_scoring_identity,
            scientific_checkpoint_identity=checkpoint_identity,
            scientific_checkpoint_content_hash="4" * 64,
            fitted_preprocessor_identity=preprocessor_identity,
            feature_schema_identity=schema_identity,
            benign_scores_ref=_artifact_ref(character=benign_character, artifact_type=ArtifactType.TEST_SCORE_SET),
            benign_sample_count=ScoreSampleCount(value=true_negative + false_positive),
            benign_content_hash=benign_character * 64,
            benign_row_order_checksum=f"benign-order-{letter}",
            attack_scores_ref=_artifact_ref(character=attack_character, artifact_type=ArtifactType.TEST_SCORE_SET),
            attack_sample_count=ScoreSampleCount(value=true_positive + false_negative),
            attack_content_hash=attack_character * 64,
            attack_row_order_checksum=f"attack-order-{letter}",
            aggregate_manifest_hash=benign_character * 64,
            score_schema_version=ArtifactSchemaVersion(value="v1"),
        ),
    )


def _confusion_entry(*, letter: str, client: ClientId) -> ClientMapEntry[ClientConfusionEvidence]:
    true_positive, false_positive, true_negative, false_negative = _CONFUSION_BY_LETTER[letter]
    return ClientMapEntry(
        client_id=client,
        value=ClientConfusionEvidence(
            true_positive=ConfusionCount(value=true_positive),
            false_positive=ConfusionCount(value=false_positive),
            true_negative=ConfusionCount(value=true_negative),
            false_negative=ConfusionCount(value=false_negative),
            calibration_sample_count=CalibrationSampleCount(value=100),
        ),
    )


def _fleet_detection_fixture() -> tuple[
    EligibleClientSet, learning_scores.TestScoreArtifactSet, ClientEvaluationMap[ClientConfusionEvidence]
]:
    letters = ("a", "b", "c")
    clients = tuple(ClientId(value=f"fleet-{letter}") for letter in letters)
    roster = ClientRoster(client_ids=clients)
    lineage = (
        SplitIdentity(value=_fingerprint("1")),
        CheckpointIdentity(value=_fingerprint("2")),
        FittedPreprocessorIdentity(value=_fingerprint("3")),
        FeatureSchemaIdentity(value=_fingerprint("4")),
        artifact_lineage.TestScoringIdentity(value=_fingerprint("5")),
    )
    split_identity, checkpoint_identity, preprocessor_identity, schema_identity, test_scoring_identity = lineage

    score_entries = tuple(
        _score_entry(letter=letter, client=client, lineage=lineage)
        for letter, client in zip(letters, clients, strict=True)
    )
    confusion_entries = tuple(
        _confusion_entry(letter=letter, client=client) for letter, client in zip(letters, clients, strict=True)
    )

    score_set = learning_scores.TestScoreArtifactSet(
        artifact_id=artifact_references.TestScoreArtifactId(value="artifact-" + "7" * 64),
        lineage=learning_scores.TestScoringLineage(
            scoring_identity=test_scoring_identity,
            context=score_lineage_context(
                ScoreLineageContextRequest(
                    roster=roster,
                    split_identity=split_identity,
                    checkpoint_identity=checkpoint_identity,
                    checkpoint_content_hash="4" * 64,
                    preprocessor_identity=preprocessor_identity,
                    schema_identity=schema_identity,
                    row_order_checksum="test-order",
                )
            ),
        ),
        per_client=learning_scores.ClientTestScoreMap(values=ClientMap(roster=roster, entries=score_entries)),
    )
    eligible_client_set = EligibleClientSet(
        roster=roster,
        protocol_eligibility_rule_identity=_fingerprint("6"),
        eligible_clients=clients,
        ineligible_reasons=(),
        identity=_fingerprint("8"),
    )
    confusion_evidence = ClientEvaluationMap(values=ClientMap(roster=roster, entries=confusion_entries))
    return eligible_client_set, score_set, confusion_evidence


def _fleet_detection_assignment(
    eligible_client_set: EligibleClientSet, *, policy: CoreThresholdPolicy = CoreThresholdPolicy.B1
) -> ThresholdAssignment:
    return ThresholdAssignment(
        policy=policy,
        per_client_tau=ThresholdAssignmentSet(
            values=ClientMap(
                roster=eligible_client_set.roster,
                entries=tuple(
                    ClientMapEntry(client_id=client, value=ThresholdValue(value=0.5))
                    for client in eligible_client_set.roster.client_ids
                ),
            )
        ),
        calibration_score_artifact_id=CalibrationScoreArtifactId(value="artifact-" + "9" * 64),
        threshold_identity=ThresholdIdentity(value=_fingerprint("a")),
        eligible_client_set_identity=eligible_client_set.identity,
        fallback_fingerprint=_fingerprint("b"),
    )


def test_fleet_detection_computes_macro_f1_p10_and_worst_client_ba_without_using_auroc() -> None:
    eligible_client_set, score_set, confusion_evidence = _fleet_detection_fixture()

    # AUROC control is supplied independently of the confusion counts, proving it is carried through as a
    # control value rather than derived from (or feeding back into) the F1/balanced-accuracy verdict path.
    result = PolicyEvaluator().evaluate(
        EvaluatePolicyRequest(
            policy=CoreThresholdPolicy.B1,
            evaluation_identity=_fingerprint("c"),
            score_set=score_set,
            assignment=_fleet_detection_assignment(eligible_client_set),
            eligible_client_set=eligible_client_set,
            confusion_evidence=confusion_evidence,
            auroc_control=AuRocScore(value=0.42),
            zero_mean_cv_wording_outcome=ClaimOutcome.NULL,
            cluster_dispersion=None,
        )
    )

    assert result.fleet_detection.macro_f1.value == pytest.approx((1.0 + 0.8 + 0.5) / 3)
    assert result.fleet_detection.p10_macro_f1.value == pytest.approx(0.5)
    assert result.fleet_detection.worst_client_balanced_accuracy.value == pytest.approx(0.5)
    assert result.fleet_detection.auroc_control == AuRocScore(value=0.42)


def test_paired_policies_reuse_one_eligible_set_and_test_score_set() -> None:
    eligible_client_set, score_set, confusion_evidence = _fleet_detection_fixture()
    evaluator = PolicyEvaluator()

    def _evaluate(policy: CoreThresholdPolicy) -> EvaluatePolicyRequest:
        return EvaluatePolicyRequest(
            policy=policy,
            evaluation_identity=_fingerprint("c"),
            score_set=score_set,
            assignment=_fleet_detection_assignment(eligible_client_set, policy=policy),
            eligible_client_set=eligible_client_set,
            confusion_evidence=confusion_evidence,
            auroc_control=AuRocScore(value=0.9),
            zero_mean_cv_wording_outcome=ClaimOutcome.NULL,
            cluster_dispersion=None,
        )

    b1_result = evaluator.evaluate(_evaluate(CoreThresholdPolicy.B1))
    b2_result = evaluator.evaluate(_evaluate(CoreThresholdPolicy.B2))

    # A paired comparison never lets a policy change the evaluated population or the underlying test scores.
    assert b1_result.eligible_client_set.identity == b2_result.eligible_client_set.identity
    assert b1_result.eligible_client_set.identity == eligible_client_set.identity
    assert b1_result.client_results[0].false_positive_rate == b2_result.client_results[0].false_positive_rate
    assert b1_result.client_results[0].true_positive_rate == b2_result.client_results[0].true_positive_rate
