from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.federated import CalibrationSizeAblationCell
from datp_core.analysis.metrics.models import ClientMetricResult, ConfusionCounts
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import EvaluationCohort, EvidenceRole, FederatedThresholdMethod
from datp_core.core.numeric import CalibrationSize, ReplicateIndex, RowCount, ScoreValue, Seed, ThresholdValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.experiments.threshold_robustness.run import _fixed_cohort_rows_for_seed


def _client_result(client_id: str) -> ClientMetricResult:
    coordinate = fedavg_coordinate(Seed(0))
    client = client_identity(client_id)
    confusion = ConfusionCounts(
        true_negative=RowCount(9),
        false_positive=RowCount(1),
        true_positive=RowCount(0),
        false_negative=RowCount(0),
        attack_assignment_valid=True,
    )
    scores = tuple(ScoreValue(0.1) for _ in range(9)) + (ScoreValue(0.9),)
    labels = tuple(PopulationOutcomeLabel.BENIGN for _ in range(10))
    return ClientMetricResult(
        coordinate=coordinate,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        client=client,
        cohort=EvaluationCohort.FPR_EVALUABLE,
        threshold=ThresholdValue(0.5),
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=EvidenceRole.SUPPORTIVE,
        evaluation_score_checksum=Checksum("a" * 64),
        evaluation_label_checksum=Checksum("b" * 64),
        source_row_checksum=Checksum("c" * 64),
    )


def _cell(size: int, client_ids: tuple[str, ...]) -> CalibrationSizeAblationCell:
    clients = tuple(_client_result(client_id) for client_id in client_ids)
    return CalibrationSizeAblationCell(
        calibration_size=CalibrationSize(size),
        replicate_index=ReplicateIndex(0),
        method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        clients=clients,
        population=calculate_population_metrics(clients),
    )


def test_fixed_cohort_rows_restrict_to_the_intersection_across_sizes() -> None:
    cells = (
        _cell(50, ("c1", "c2", "c3", "c4")),
        _cell(100, ("c1", "c2", "c3")),
        _cell(250, ("c1", "c2")),
    )
    rows = _fixed_cohort_rows_for_seed(Seed(0), FederatedThresholdMethod.LOCAL_THRESHOLD, cells)
    assert len(rows) == 3
    assert all(row.intersection_client_count.value == 2 for row in rows)
    assert all(row.coverage.value == 2 / 4 for row in rows)
    assert {row.calibration_size.value for row in rows} == {50, 100, 250}


def test_fixed_cohort_rows_are_empty_when_no_client_is_feasible_at_every_size() -> None:
    cells = (
        _cell(50, ("c1",)),
        _cell(100, ("c2",)),
    )
    rows = _fixed_cohort_rows_for_seed(Seed(0), FederatedThresholdMethod.LOCAL_THRESHOLD, cells)
    assert rows == ()
