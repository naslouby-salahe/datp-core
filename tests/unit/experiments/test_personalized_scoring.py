from pathlib import Path

import polars as pl
import pytest
from tests.unit.learning.federated.helpers import benign_frame, client_identity, fedavg_coordinate, fitted_state

from datp_core.analysis.metrics.cohorts import (
    ClientEligibilityRecord,
    ClientExclusionReason,
    EvaluationCohortManifest,
    EvaluationCohortMembership,
)
from datp_core.analysis.metrics.models import AvailableMetric, metric_by_id
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    CheckpointStatus,
    EvaluationCohort,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    PopulationId,
    PublicationStatus,
    ScoreFrameColumn,
    SerializationFormat,
)
from datp_core.core.numeric import FeatureCount, RoundNumber, RowCount, Seed, ThresholdValue
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.data.preprocessing.models import ClientPreprocessingResult, PreprocessedPartitionPaths
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreRecord
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest
from datp_core.experiments.personalized_scoring import client_metric, client_scoring_input, score_record_for_client
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT
from datp_core.thresholds.contracts import ThresholdAssignment

_POPULATION = PopulationId.NBAIOT_NATURAL_DEVICES
_SEED = Seed(0)


def _score_record(role: PartitionRole, client_id: str, path: Path) -> ScoreRecord:
    return ScoreRecord(
        coordinate=fedavg_coordinate(_SEED),
        scored_client=client_identity(client_id),
        partition_role=role,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        path=path,
        checksum=Checksum("b" * 64),
        row_count=RowCount(4),
        feature_count=FeatureCount(1),
        serialization_format=SerializationFormat.PARQUET,
    )


def test_score_record_for_client_returns_the_single_match(tmp_path: Path) -> None:
    record = _score_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet")
    resolved = score_record_for_client((record,), client_identity("client_a"), PartitionRole.EVALUATION)
    assert resolved is record


def test_score_record_for_client_raises_when_client_is_absent(tmp_path: Path) -> None:
    record = _score_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet")
    with pytest.raises(ScientificContractError):
        score_record_for_client((record,), client_identity("client_b"), PartitionRole.EVALUATION)


def _client_preprocessing_result(client_id: str, tmp_path: Path) -> ClientPreprocessingResult:
    calibration_path = tmp_path / f"{client_id}_calibration.parquet"
    evaluation_path = tmp_path / f"{client_id}_evaluation.parquet"
    benign_frame(RowCount(4)).write_parquet(calibration_path)
    benign_frame(RowCount(4)).write_parquet(evaluation_path)
    state = fitted_state(tmp_path / f"{client_id}_state.skops", client_id)
    return ClientPreprocessingResult(
        client_identity=state.client_identity,
        paths=PreprocessedPartitionPaths(
            train=tmp_path / f"{client_id}_train.parquet",
            calibration=calibration_path,
            evaluation=evaluation_path,
            future_recalibration=None,
            static_reference_reserve=None,
        ),
        fitted_state=state,
        publication_status=PublicationStatus.PUBLISHED,
        train_row_count=RowCount(4),
        calibration_row_count=RowCount(4),
        evaluation_row_count=RowCount(4),
        future_recalibration_row_count=RowCount(0),
        static_reference_reserve_row_count=RowCount(0),
    )


def test_client_scoring_input_reads_the_matching_client_publication(tmp_path: Path) -> None:
    publication = _client_preprocessing_result("client_a", tmp_path)
    result = client_scoring_input((publication,), client_identity("client_a"))
    assert result.client == client_identity("client_a")
    assert result.calibration_features.height == 4
    assert result.evaluation_features.height == 4


def test_client_scoring_input_raises_when_publication_is_ambiguous(tmp_path: Path) -> None:
    publication = _client_preprocessing_result("client_a", tmp_path)
    with pytest.raises(ScientificContractError):
        client_scoring_input((publication, publication), client_identity("client_a"))


def _evaluation_frame(*, benign_count: int, attack_count: int) -> pl.DataFrame:
    labels = [PopulationOutcomeLabel.BENIGN.value] * benign_count + [PopulationOutcomeLabel.ATTACK.value] * attack_count
    scores = [0.1] * benign_count + [5.0] * attack_count
    row_count = benign_count + attack_count
    return pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: [f"eval-{index}" for index in range(row_count)],
            ScoreFrameColumn.OUTCOME_LABEL.value: labels,
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: scores,
        }
    )


def _calibration_frame(benign_count: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: [f"cal-{index}" for index in range(benign_count)],
            ScoreFrameColumn.OUTCOME_LABEL.value: [PopulationOutcomeLabel.BENIGN.value] * benign_count,
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: [0.1] * benign_count,
        }
    )


def _manifest_with_scores(tmp_path: Path) -> FederatedScoreArtifactManifest:
    coordinate = fedavg_coordinate(_SEED)
    client = client_identity("device_a")
    calibration_path = tmp_path / "cal.parquet"
    evaluation_path = tmp_path / "eval.parquet"
    _calibration_frame(100).write_parquet(calibration_path)
    _evaluation_frame(benign_count=10, attack_count=5).write_parquet(evaluation_path)
    return ScoreArtifactManifest(
        coordinate=coordinate,
        scored_split_protocol=coordinate.split_protocol,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        preprocessing_state_set_checksum=Checksum("c" * 64),
        split_manifest_checksum=Checksum("d" * 64),
        calibration_records=(
            ScoreRecord(
                coordinate=coordinate,
                scored_client=client,
                partition_role=PartitionRole.CALIBRATION,
                checkpoint_round=RoundNumber(2),
                checkpoint_checksum=Checksum("a" * 64),
                path=calibration_path,
                checksum=Checksum("b" * 64),
                row_count=RowCount(100),
                feature_count=FeatureCount(1),
                serialization_format=SerializationFormat.PARQUET,
            ),
        ),
        evaluation_records=(
            ScoreRecord(
                coordinate=coordinate,
                scored_client=client,
                partition_role=PartitionRole.EVALUATION,
                checkpoint_round=RoundNumber(2),
                checkpoint_checksum=Checksum("a" * 64),
                path=evaluation_path,
                checksum=Checksum("e" * 64),
                row_count=RowCount(15),
                feature_count=FeatureCount(1),
                serialization_format=SerializationFormat.PARQUET,
            ),
        ),
    )


def _cohort_manifest(client: ClientIdentity, *, fpr_evaluable: bool = True) -> EvaluationCohortManifest:
    eligibility = ClientEligibilityRecord(
        client=client,
        benign_calibration_count=RowCount(100),
        benign_evaluation_count=RowCount(10),
        attack_evaluation_count=RowCount(5),
        calibration_eligible=fpr_evaluable,
        fpr_evaluable=fpr_evaluable,
        attack_evaluable=True,
        deployment_fallback=not fpr_evaluable,
        exclusion_reasons=() if fpr_evaluable else (ClientExclusionReason.DEPLOYMENT_FALLBACK_ONLY,),
    )
    if fpr_evaluable:
        cohort = EvaluationCohort.FPR_EVALUABLE
        reasons: tuple[ClientExclusionReason, ...] = ()
    else:
        cohort = EvaluationCohort.DEPLOYMENT_FALLBACK
        reasons = (ClientExclusionReason.DEPLOYMENT_FALLBACK_ONLY,)
    return EvaluationCohortManifest(
        population=_POPULATION,
        partition_seed=_SEED,
        minimum_benign_calibration_support=MINIMUM_BENIGN_SUPPORT,
        records=(eligibility,),
        memberships=(EvaluationCohortMembership(client=client, cohort=cohort, reasons=reasons),),
    )


def test_client_metric_computes_a_fpr_evaluable_result(tmp_path: Path) -> None:
    manifest = _manifest_with_scores(tmp_path)
    client = client_identity("device_a")
    assignment = ThresholdAssignment(client=client, threshold=ThresholdValue(1.0))
    cohort = _cohort_manifest(client)

    metric = client_metric(
        manifest.coordinate,
        FederatedThresholdMethod.SHARED_THRESHOLD,
        manifest,
        assignment,
        cohort,
    )

    assert metric.client == client
    assert metric.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD
    assert metric.confusion.true_negative.value + metric.confusion.false_positive.value == 10
    assert metric.confusion.true_positive.value + metric.confusion.false_negative.value == 5
    fpr = metric_by_id(metric.metrics, MetricId.FALSE_POSITIVE_RATE)
    assert isinstance(fpr, AvailableMetric)
    assert fpr.value.value == 0.0
