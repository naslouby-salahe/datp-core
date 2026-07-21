"""Training tensors are derived only from the authorized materialized split."""

from pathlib import Path

import polars as pl

from datp_core.infrastructure.learning.pytorch_adapter import load_benign_client_tensors


def test_loader_excludes_calibration_test_and_attack_rows_and_sorts_clients(tmp_path: Path) -> None:
    path = tmp_path / "materialized.parquet"
    pl.DataFrame(
        {
            "split": ["train", "train", "calibration", "test"],
            "client_id": ["b", "a", "a", "a"],
            "is_attack": [False, False, False, True],
            "feature": [2.0, 1.0, 3.0, 4.0],
        }
    ).write_parquet(path)

    tensors = load_benign_client_tensors(path, "train", ("feature",))

    assert [client_id for client_id, _ in tensors] == ["a", "b"]
    assert tensors[0][1].tolist() == [[1.0]]
    assert tensors[1][1].tolist() == [[2.0]]


def test_loader_selects_only_benign_calibration_rows(tmp_path: Path) -> None:
    path = tmp_path / "materialized.parquet"
    pl.DataFrame(
        {
            "split": ["train", "calibration", "calibration", "test"],
            "client_id": ["a", "a", "b", "a"],
            "is_attack": [False, False, True, False],
            "feature": [1.0, 2.0, 3.0, 4.0],
        }
    ).write_parquet(path)

    tensors = load_benign_client_tensors(path, "calibration", ("feature",))

    assert [(client_id, tensor.tolist()) for client_id, tensor in tensors] == [("a", [[2.0]])]
