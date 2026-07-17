from hashlib import sha256
from math import isclose

from datp_core.analysis.report_models import ReportColumn, ReportRow, TableSpecification
from datp_core.application.ports.reporting import RenderReportArtifactRequest
from datp_core.application.reporting.contracts import TracedReportSpecification
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
    ReportIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
    StageFingerprint,
)
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount, ConfusionCount
from datp_core.domain.evaluation.operating_points import CentralizedPolicyEvaluationResult, EligibleClientSet
from datp_core.domain.evaluation.statistical_results import AuRocScore, ClaimOutcome
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.experiments.protocols import ReportArtifactType, TableType
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
from datp_core.domain.thresholding.policies import CentralizedThresholdAssignment, ThresholdValue
from datp_core.infrastructure.reporting.markdown import MarkdownReportRenderer


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


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


def _evaluate_b0(
    *, threshold_identity_character: str
) -> tuple[CentralizedPolicyEvaluationResult, CentralizedThresholdAssignment]:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    roster = ClientRoster(client_ids=(client_a, client_b))

    assignment = CentralizedThresholdAssignment(
        tau=ThresholdValue(value=1.5),
        centralized_calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("4")),
        threshold_identity=CentralizedThresholdIdentity(value=_fingerprint(threshold_identity_character)),
    )
    eligible_set = EligibleClientSet(
        roster=roster,
        protocol_eligibility_rule_identity=_fingerprint("e"),
        eligible_clients=(client_a, client_b),
        ineligible_reasons=(),
        identity=_fingerprint("f"),
    )
    confusion_map = ClientEvaluationMap(
        values=ClientMap(
            roster=roster,
            entries=(
                ClientMapEntry(
                    client_id=client_a,
                    value=ClientConfusionEvidence(
                        true_positive=ConfusionCount(value=8),
                        false_positive=ConfusionCount(value=2),
                        true_negative=ConfusionCount(value=8),
                        false_negative=ConfusionCount(value=2),
                        calibration_sample_count=CalibrationSampleCount(value=50),
                    ),
                ),
                ClientMapEntry(
                    client_id=client_b,
                    value=ClientConfusionEvidence(
                        true_positive=ConfusionCount(value=9),
                        false_positive=ConfusionCount(value=1),
                        true_negative=ConfusionCount(value=9),
                        false_negative=ConfusionCount(value=1),
                        calibration_sample_count=CalibrationSampleCount(value=60),
                    ),
                ),
            ),
        )
    )
    request = EvaluateCentralizedPolicyRequest(
        policy=ThresholdComparatorRole.CENTRALIZED_MODEL_B0,
        evaluation_identity=CentralizedEvaluationIdentity(value=_fingerprint("1")),
        score_artifacts=(
            _test_artifact(client_id=client_a, character="2"),
            _test_artifact(client_id=client_b, character="3"),
        ),
        assignment=assignment,
        eligible_client_set=eligible_set,
        confusion_evidence=confusion_map,
        auroc_control=AuRocScore(value=0.9),
        zero_mean_cv_wording_outcome=ClaimOutcome.WEAK_POSITIVE,
        cluster_dispersion=None,
    )
    return PolicyEvaluator().evaluate_centralized(request), assignment


def _comparator_table(result: CentralizedPolicyEvaluationResult) -> TableSpecification:
    return TableSpecification(
        table_type=TableType.COMPARATOR,
        columns=(
            ReportColumn(key="client_id", label="Client"),
            ReportColumn(key="false_positive_rate", label="FPR"),
            ReportColumn(key="true_positive_rate", label="TPR"),
        ),
        rows=tuple(
            ReportRow(
                values=(
                    client_result.client_id.value,
                    client_result.false_positive_rate.value,
                    client_result.true_positive_rate.value,
                )
            )
            for client_result in result.client_results
        ),
    )


def _report_identity(
    *, evaluation_identity: CentralizedEvaluationIdentity, threshold_identity: CentralizedThresholdIdentity
) -> ReportIdentity:
    digest = sha256(f"{evaluation_identity.value.value}:{threshold_identity.value.value}".encode()).hexdigest()
    return ReportIdentity(value=StageFingerprint(value=digest))


def _rendered_content(*, table: TableSpecification, report_identity: ReportIdentity) -> str:
    output = ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{report_identity.value.value}"),
        artifact_type=ArtifactType.RENDERED_TABLE,
        content_hash=report_identity.value.value,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.MARKDOWN,
    )
    rendered = MarkdownReportRenderer().render(
        RenderReportArtifactRequest(
            traced_specification=TracedReportSpecification(
                specification=table,
                output=output,
                result_freeze=output,
                provenance_chain=ArtifactReferenceCollection(references=(output,)),
            ),
            artifact_type=ReportArtifactType.MAIN_TABLE,
            format=SerializationFormat.MARKDOWN,
        )
    )
    return rendered.content.decode()


def test_b0_centralized_result_renders_through_the_generic_comparator_table_route() -> None:
    result, assignment = _evaluate_b0(threshold_identity_character="5")
    table = _comparator_table(result)
    report_identity = _report_identity(
        evaluation_identity=result.evaluation_identity, threshold_identity=assignment.threshold_identity
    )

    content = _rendered_content(table=table, report_identity=report_identity)

    assert "client-a" in content
    assert "client-b" in content
    assert table.table_type is TableType.COMPARATOR


def test_b0_report_identity_retains_centralized_lineage_and_changes_with_threshold_identity() -> None:
    first_result, first_assignment = _evaluate_b0(threshold_identity_character="5")
    second_result, second_assignment = _evaluate_b0(threshold_identity_character="6")

    first_identity = _report_identity(
        evaluation_identity=first_result.evaluation_identity, threshold_identity=first_assignment.threshold_identity
    )
    second_identity = _report_identity(
        evaluation_identity=second_result.evaluation_identity, threshold_identity=second_assignment.threshold_identity
    )

    assert type(first_result.evaluation_identity) is CentralizedEvaluationIdentity
    assert first_identity != second_identity
    assert isclose(first_result.fleet_dispersion.worst_client_fpr.value, 0.2)
