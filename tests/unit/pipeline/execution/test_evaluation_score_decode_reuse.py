from pathlib import Path

import polars as pl
import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.federated_execution import _score_arrays
from datp_core.core.identifiers import PartitionRole, ScoreArtifactPathText, ScoreFrameColumn, SerializationFormat
from datp_core.core.numeric import FeatureCount, RowCount, Seed
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.detector.scoring.contracts import ScoreRecord
from datp_core.experiments.execution.workspace import _load_benign_evaluation_scores


@pytest.fixture(autouse=True)
def _clear_evaluation_score_cache():
    _load_benign_evaluation_scores.cache_clear()
    _score_arrays.cache_clear()
    yield
    _load_benign_evaluation_scores.cache_clear()
    _score_arrays.cache_clear()


def _record(tmp_path: Path) -> ScoreRecord:
    coordinate = fedavg_coordinate(Seed(0))
    client = client_identity("client_a")
    path = tmp_path / "evaluation.parquet"
    pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: ["row-0", "row-1"],
            ScoreFrameColumn.OUTCOME_LABEL.value: [
                PopulationOutcomeLabel.BENIGN.value,
                PopulationOutcomeLabel.ATTACK.value,
            ],
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: [0.1, 0.9],
        }
    ).write_parquet(path)
    return ScoreRecord(
        coordinate=coordinate,
        partition_role=PartitionRole.EVALUATION,
        path=path,
        row_count=RowCount(2),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
        scored_client=client,
    )


def test_load_benign_evaluation_scores_decodes_the_parquet_file_only_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    record = _record(tmp_path)
    read_calls: list[Path] = []
    original_read_parquet = pl.read_parquet

    def _counting_read_parquet(path, *args, **kwargs):
        read_calls.append(Path(path))
        return original_read_parquet(path, *args, **kwargs)

    monkeypatch.setattr("datp_core.experiments.execution.workspace.pl.read_parquet", _counting_read_parquet)

    first = _load_benign_evaluation_scores(record)
    second = _load_benign_evaluation_scores(record)

    assert first == second
    assert len(first) == 1
    assert first[0].stable_row_id == "row-0"
    assert len(read_calls) == 1


def test_federated_evaluation_decodes_fixed_score_arrays_only_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    record = _record(tmp_path)
    read_calls: list[Path] = []
    original_read_parquet = pl.read_parquet

    def _counting_read_parquet(path, *args, **kwargs):
        read_calls.append(Path(path))
        return original_read_parquet(path, *args, **kwargs)

    monkeypatch.setattr("datp_core.analysis.metrics.federated_execution.pl.read_parquet", _counting_read_parquet)

    first = _score_arrays(ScoreArtifactPathText(str(record.path)))
    second = _score_arrays(ScoreArtifactPathText(str(record.path)))

    assert first == second
    assert len(read_calls) == 1


def test_load_benign_evaluation_scores_raises_explicitly_when_evidence_is_missing(tmp_path: Path) -> None:
    record = _record(tmp_path)
    record.path.unlink()

    with pytest.raises(Exception, match="evaluation score evidence is unavailable"):
        _load_benign_evaluation_scores(record)
