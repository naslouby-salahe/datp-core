from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import AUTOENCODER, FEATURE_NAMES, benign_frame

from datp_core.core.identifiers import PartitionRole
from datp_core.core.numeric import BatchSize, RowCount, Seed
from datp_core.detector.autoencoder import build_reconstruction_autoencoder
from datp_core.detector.scoring import frames as frames_module
from datp_core.runtime.compute import LEARNING_DEVICE


def _model(device):
    model = build_reconstruction_autoencoder(AUTOENCODER, initialization_seed=Seed(0)).to(device)
    model.eval()
    return model


def test_score_and_persist_autoencoder_frame_does_not_reread_the_written_parquet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    device = LEARNING_DEVICE
    model = _model(device)
    frame = benign_frame(RowCount(4), seed=Seed(0))
    destination = tmp_path / "calibration.parquet"

    def _fail_if_reread(*args: object, **kwargs: object) -> None:
        pytest.fail("score publication must not re-read the just-written parquet file")

    monkeypatch.setattr(frames_module.pl, "read_parquet", _fail_if_reread)

    persisted = frames_module.score_and_persist_autoencoder_frame(
        frame=frame,
        partition_role=PartitionRole.CALIBRATION,
        feature_names=FEATURE_NAMES,
        model=model,
        batch_size=BatchSize(4),
        device=device,
        destination=destination,
    )

    assert persisted.path == destination
    assert persisted.row_count == RowCount(4)
    assert destination.is_file()


def test_score_and_persist_autoencoder_frame_raises_on_row_count_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    device = LEARNING_DEVICE
    model = _model(device)
    frame = benign_frame(RowCount(4), seed=Seed(0))
    destination = tmp_path / "calibration.parquet"

    class _FakeMetadata:
        num_rows = 999

    class _FakeParquetFile:
        def __init__(self, _path: object) -> None:
            self.metadata = _FakeMetadata()

    monkeypatch.setattr(frames_module.pq, "ParquetFile", _FakeParquetFile)

    with pytest.raises(Exception, match="row count mismatch"):
        frames_module.score_and_persist_autoencoder_frame(
            frame=frame,
            partition_role=PartitionRole.CALIBRATION,
            feature_names=FEATURE_NAMES,
            model=model,
            batch_size=BatchSize(4),
            device=device,
            destination=destination,
        )
