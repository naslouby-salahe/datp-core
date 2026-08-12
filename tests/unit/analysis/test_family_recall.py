from pathlib import Path
from types import SimpleNamespace
from typing import cast

import polars as pl
import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.mechanisms.family_recall import compare_family_recall_policies
from datp_core.analysis.metrics.family_recall import (
    FamilyRecallApplicability,
    FamilyRecallDiagnostics,
    FamilyRecallRecord,
    FamilyRecallSummary,
    WorstFamilyClientRecall,
    evaluate_nbaiot_family_recall,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import ClientMetricResult
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, PartitionRole, ScoreFrameColumn, SerializationFormat
from datp_core.core.numeric import FeatureCount, Ratio, RowCount, Seed, ThresholdValue
from datp_core.data.nbaiot.schema import NBaIoTAttackFamily
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreRecord
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


def test_nbaiot_family_recall_uses_held_out_family_rows_and_client_threshold(tmp_path: Path) -> None:
    manifest, client = _manifest(tmp_path)

    diagnostics = evaluate_nbaiot_family_recall(
        manifest,
        (cast(ClientMetricResult, SimpleNamespace(client=client, threshold=ThresholdValue(0.5))),),
    )

    assert diagnostics.applicability is FamilyRecallApplicability.APPLICABLE
    observed_records = [
        (item.family.value, item.support_count.value, item.true_positive_rate.value) for item in diagnostics.records
    ]
    assert observed_records == [
        ("gafgyt", 2, 0.5),
        ("mirai", 2, 0.5),
    ]
    assert [(item.family.value, item.macro_family_true_positive_rate.value) for item in diagnostics.summaries] == [
        ("gafgyt", 0.5),
        ("mirai", 0.5),
    ]
    assert diagnostics.worst_family_client is not None
    assert diagnostics.worst_family_client.family.value == "gafgyt"


def test_nbaiot_family_recall_rejects_attack_rows_without_family_provenance(tmp_path: Path) -> None:
    manifest, client = _manifest(tmp_path, missing_attack_family=True)

    with pytest.raises(ScientificContractError, match="attack-family provenance"):
        evaluate_nbaiot_family_recall(
            manifest,
            (cast(ClientMetricResult, SimpleNamespace(client=client, threshold=ThresholdValue(0.5))),),
        )


def test_family_recall_compares_each_policy_to_shared_on_the_fixed_client_family_cohort() -> None:
    client = client_identity("client_a")
    documents = tuple(
        cast(
            FederatedEvaluationDocument,
            SimpleNamespace(
                threshold_method=method,
                score_coordinate=SimpleNamespace(
                    population=fedavg_coordinate(Seed(0)).population,
                    training_seed=Seed(0),
                ),
                diagnostics=SimpleNamespace(family_recall=_diagnostics(client, rate)),
            ),
        )
        for method, rate in (
            (FederatedThresholdMethod.SHARED_THRESHOLD, 0.5),
            (FederatedThresholdMethod.LOCAL_THRESHOLD, 1.0),
            (FederatedThresholdMethod.FAMILY_THRESHOLD, 0.0),
            (FederatedThresholdMethod.CLUSTER_THRESHOLD, 0.5),
        )
    )

    comparison = compare_family_recall_policies(documents)

    assert len(comparison.policies) == 4
    differences = [
        (item.compared_method, item.compared_minus_shared_true_positive_rate.value)
        for item in comparison.shared_differences
    ]
    assert differences == [
        (FederatedThresholdMethod.CLUSTER_THRESHOLD, 0.0),
        (FederatedThresholdMethod.FAMILY_THRESHOLD, -0.5),
        (FederatedThresholdMethod.LOCAL_THRESHOLD, 0.5),
    ]


def _diagnostics(client: ClientIdentity, rate: float) -> FamilyRecallDiagnostics:
    record = FamilyRecallRecord(
        client=client,
        family=NBaIoTAttackFamily.MIRAI,
        support_count=RowCount(2),
        true_positive_count=RowCount(int(rate * 2)),
        false_negative_count=RowCount(2 - int(rate * 2)),
        true_positive_rate=Ratio(rate),
        false_negative_rate=Ratio(1.0 - rate),
    )
    return FamilyRecallDiagnostics(
        applicability=FamilyRecallApplicability.APPLICABLE,
        records=(record,),
        summaries=(
            FamilyRecallSummary(
                family=record.family,
                supported_client_count=RowCount(1),
                macro_family_true_positive_rate=record.true_positive_rate,
            ),
        ),
        worst_family_client=WorstFamilyClientRecall(
            client=client,
            family=record.family,
            true_positive_rate=record.true_positive_rate,
        ),
    )


def _manifest(
    tmp_path: Path, *, missing_attack_family: bool = False
) -> tuple[ScoreArtifactManifest, ClientIdentity]:
    coordinate = fedavg_coordinate(Seed(0))
    client = client_identity("client_a")
    calibration_path = tmp_path / "calibration.parquet"
    evaluation_path = tmp_path / "evaluation.parquet"
    _score_frame(
        ["calibration-0"],
        [PopulationOutcomeLabel.BENIGN.value],
        [None],
        [0.1],
    ).write_parquet(calibration_path)
    _score_frame(
        ["evaluation-0", "evaluation-1", "evaluation-2", "evaluation-3"],
        [PopulationOutcomeLabel.ATTACK.value] * 4,
        ["gafgyt", "gafgyt", "mirai", None if missing_attack_family else "mirai"],
        [0.9, 0.1, 0.9, 0.1],
    ).write_parquet(evaluation_path)
    return (
        ScoreArtifactManifest(
            coordinate=coordinate,
            scored_split_protocol=coordinate.split_protocol,
            calibration_records=(_record(coordinate, client, calibration_path, PartitionRole.CALIBRATION, 1),),
            evaluation_records=(_record(coordinate, client, evaluation_path, PartitionRole.EVALUATION, 4),),
        ),
        client,
    )


def _score_frame(
    row_ids: list[str], labels: list[str], attack_families: list[str | None], scores: list[float]
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: row_ids,
            ScoreFrameColumn.OUTCOME_LABEL.value: labels,
            ScoreFrameColumn.ATTACK_FAMILY.value: attack_families,
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: scores,
        },
        schema={
            ScoreFrameColumn.STABLE_ROW_ID.value: pl.Utf8,
            ScoreFrameColumn.OUTCOME_LABEL.value: pl.Utf8,
            ScoreFrameColumn.ATTACK_FAMILY.value: pl.Utf8,
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: pl.Float64,
        },
    )


def _record(
    coordinate: FederatedTrainingCoordinate,
    client: ClientIdentity,
    path: Path,
    role: PartitionRole,
    count: int,
) -> ScoreRecord:
    return ScoreRecord(
        coordinate=coordinate,
        partition_role=role,
        path=path,
        row_count=RowCount(count),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
        scored_client=client,
    )
