from pathlib import Path
from types import SimpleNamespace
from typing import cast

import polars as pl
import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.family_recall import (
    FamilyRecallApplicability,
    evaluate_nbaiot_family_recall,
)
from datp_core.analysis.metrics.models import ClientMetricResult
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import PartitionRole, ScoreFrameColumn, SerializationFormat
from datp_core.core.numeric import FeatureCount, RowCount, Seed, ThresholdValue
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
