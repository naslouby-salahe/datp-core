"""Independent anchor observations derive historical-endpoint semantics from validated artifact provenance."""

from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.cohorts import (
    ClientEligibilityRecord,
    EvaluationCohortManifest,
    EvaluationCohortMembership,
)
from datp_core.analysis.metrics.federated import EvaluationDiagnostics, FederatedEvaluationDocument
from datp_core.analysis.metrics.fixed_score import (
    CalibrationEvidence,
    ClientAurocEvidence,
    DetectorEvidence,
    FixedScoreEvidence,
    HeldOutEvaluationEvidence,
    PopulationEvidence,
)
from datp_core.analysis.metrics.models import ClientMetricResult, ConfusionCounts
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.analysis.metrics.semantics import available
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import AnchorReproductionError
from datp_core.core.identifiers import (
    CheckpointStatus,
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    PopulationId,
    StageOperationId,
)
from datp_core.core.numeric import RoundNumber, RowCount, ScoreValue, Seed, ThresholdValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.experiments.anchor.contracts import (
    AnchorDiscrepancyReason,
    AnchorObservationSourceKind,
)
from datp_core.experiments.anchor.run import observation_from_evaluation_document
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT
from datp_core.protocols.training import CHECKPOINT_PROTOCOL

_POPULATION = PopulationId.NBAIOT_NATURAL_DEVICES
_SEED = Seed(0)


def _client_result(client_id: str) -> ClientMetricResult:
    coordinate = fedavg_coordinate(_SEED)
    client = client_identity(client_id)
    confusion = ConfusionCounts(
        true_negative=RowCount(1),
        false_positive=RowCount(1),
        true_positive=RowCount(1),
        false_negative=RowCount(0),
        attack_assignment_valid=True,
    )
    scores = (ScoreValue(0.1), ScoreValue(0.9), ScoreValue(0.9))
    labels = (
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.ATTACK,
    )
    return ClientMetricResult(
        coordinate=coordinate,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        client=client,
        cohort=EvaluationCohort.FPR_EVALUABLE,
        threshold=ThresholdValue(0.5),
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=EvidenceRole.CONFIRMATORY,
        evaluation_score_checksum=Checksum("a" * 64),
        evaluation_label_checksum=Checksum("b" * 64),
        source_row_checksum=Checksum("c" * 64),
    )


def _cohort_manifest(client) -> EvaluationCohortManifest:
    return EvaluationCohortManifest(
        population=_POPULATION,
        partition_seed=_SEED,
        minimum_benign_calibration_support=MINIMUM_BENIGN_SUPPORT,
        records=(
            ClientEligibilityRecord(
                client=client,
                benign_calibration_count=RowCount(100),
                benign_evaluation_count=RowCount(10),
                attack_evaluation_count=RowCount(5),
                calibration_eligible=True,
                fpr_evaluable=True,
                attack_evaluable=True,
                deployment_fallback=False,
                exclusion_reasons=(),
            ),
        ),
        memberships=(EvaluationCohortMembership(client=client, cohort=EvaluationCohort.FPR_EVALUABLE, reasons=()),),
    )


def _fixed_score_evidence() -> FixedScoreEvidence:
    checksum = Checksum("d" * 64)
    return FixedScoreEvidence(
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        detector=DetectorEvidence(
            coordinate=fedavg_coordinate(Seed(8)),
            model_checksum=checksum,
            preprocessing_checksum=checksum,
            selected_checkpoint_checksum=checksum,
        ),
        calibration=CalibrationEvidence(role=PartitionRole.CALIBRATION, score_checksum=checksum),
        evaluation=HeldOutEvaluationEvidence(
            score_checksum=checksum,
            label_checksum=checksum,
            source_row_checksum=checksum,
            score_order_checksum=checksum,
            aurocs=(ClientAurocEvidence(client_identity("device_a"), available(MetricId.AUROC, 0.8)),),
        ),
        population=PopulationEvidence(
            client_inventory_checksum=checksum,
            eligibility_cohort_checksum=checksum,
        ),
    )


def _document(
    *,
    checkpoint_round: RoundNumber,
    checkpoint_status: CheckpointStatus,
) -> FederatedEvaluationDocument:
    client = client_identity("device_a")
    client_result = _client_result("device_a")
    return FederatedEvaluationDocument(
        stage=StageOperationId.EVALUATE_FEDERATED,
        score_coordinate=fedavg_coordinate(_SEED),
        score_checkpoint_round=checkpoint_round,
        score_checkpoint_checksum=Checksum("e" * 64),
        score_checkpoint_status=checkpoint_status,
        preprocessing_state_set_checksum=Checksum("f" * 64),
        split_manifest_checksum=Checksum("g" * 64),
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        evidence_role=EvidenceRole.CONFIRMATORY,
        fixed_score_evidence=_fixed_score_evidence(),
        cohort=_cohort_manifest(client),
        clients=(client_result,),
        population=calculate_population_metrics((client_result,)),
        diagnostics=EvaluationDiagnostics(
            conformal_coverage=(),
            threshold_estimation=(),
            communication=None,
            alert_burden=(),
        ),
        temporal_provenance=None,
    )


def _write_document(tmp_path: Path, document: FederatedEvaluationDocument) -> Path:
    path = tmp_path / "evaluation.json"
    path.write_text(document.model_dump_json(), encoding="utf-8")
    return path


def test_terminal_non_test_checkpoint_derives_historical_endpoint_observation(tmp_path: Path) -> None:
    document = _document(
        checkpoint_round=CHECKPOINT_PROTOCOL.maximum_round,
        checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )
    path = _write_document(tmp_path, document)

    observation = observation_from_evaluation_document(document, document_path=path)

    assert observation.checkpoint_status is CheckpointStatus.HISTORICAL_ENDPOINT
    assert observation.source_kind is AnchorObservationSourceKind.INDEPENDENT_REPRODUCTION
    assert observation.model_checkpoint_identity == document.score_checkpoint_checksum
    assert observation.artifact_path == path.resolve()


def test_non_terminal_checkpoint_round_is_rejected(tmp_path: Path) -> None:
    document = _document(
        checkpoint_round=RoundNumber(150),
        checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )
    path = _write_document(tmp_path, document)

    with pytest.raises(AnchorReproductionError, match="checkpoint") as exc:
        observation_from_evaluation_document(document, document_path=path)
    assert exc.value.reason == AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS.value


def test_stability_evidence_checkpoint_status_is_rejected(tmp_path: Path) -> None:
    document = _document(
        checkpoint_round=CHECKPOINT_PROTOCOL.maximum_round,
        checkpoint_status=CheckpointStatus.STABILITY_EVIDENCE,
    )
    path = _write_document(tmp_path, document)

    with pytest.raises(AnchorReproductionError, match="checkpoint") as exc:
        observation_from_evaluation_document(document, document_path=path)
    assert exc.value.reason == AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS.value
