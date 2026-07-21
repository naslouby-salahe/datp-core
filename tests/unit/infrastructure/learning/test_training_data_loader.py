"""Training tensors are derived only from the authorized materialized split."""

from pathlib import Path

import polars as pl
import torch

from datp_core.infrastructure.learning.pytorch_adapter import load_benign_client_tensors, score_materialized_split


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


def test_score_materialized_split_preserves_identity_and_excludes_calibration_attacks(tmp_path: Path) -> None:
    path = tmp_path / "materialized.parquet"
    pl.DataFrame(
        {
            "split": ["calibration", "test", "test"],
            "client_id": ["a", "a", "a"],
            "is_attack": [False, False, True],
            "source_path": ["source.csv", "source.csv", "source.csv"],
            "source_row_index": [1, 2, 3],
            "feature": [2.0, 3.0, 4.0],
        }
    ).write_parquet(path)

    calibration = score_materialized_split(
        torch.nn.Identity(), path, split="calibration", feature_columns=("feature",), batch_size=8, device="cpu"
    )
    test = score_materialized_split(
        torch.nn.Identity(), path, split="test", feature_columns=("feature",), batch_size=8, device="cpu"
    )

    assert calibration.to_dicts() == [
        {
            "source_path": "source.csv",
            "source_row_index": 1,
            "client_id": "a",
            "split": "calibration",
            "label": 0,
            "score": 0.0,
        }
    ]
    assert test["label"].to_list() == [0, 1]
    assert test["source_row_index"].to_list() == [2, 3]
