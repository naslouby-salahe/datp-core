"""Reconstruction score computation: per-sample MSE over materialized splits."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import polars as pl
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.learning.scoring.data import _score_input_frame, _score_output_frame


def compute_reconstruction_scores(
    model: nn.Module,
    data: torch.Tensor,
    batch_size: int,
    device: str,
) -> torch.Tensor:
    """Compute per-sample mean squared reconstruction error scores."""
    model = model.to(device)
    model.eval()
    dataset = TensorDataset(data)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    scores_list = []

    with torch.no_grad():
        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            recon = model(batch_x)
            err = torch.mean((recon - batch_x) ** 2, dim=1)
            scores_list.append(err.cpu())

    return torch.cat(scores_list, dim=0)


def score_materialized_split(
    model: nn.Module,
    path: Path,
    *,
    split: str,
    feature_columns: tuple[str, ...],
    batch_size: int,
    device: str,
) -> pl.DataFrame:
    """Score one materialized split while retaining its immutable row identity."""
    selected = _score_input_frame(path, split=split, feature_columns=feature_columns)
    values = selected.select(*feature_columns).to_numpy()
    scores = compute_reconstruction_scores(
        model,
        torch.tensor(values, dtype=torch.float32),
        batch_size=batch_size,
        device=device,
    ).numpy()
    return _score_output_frame(selected, scores)


def score_personalized_materialized_split(
    models: Mapping[str, nn.Module],
    path: Path,
    *,
    split: str,
    feature_columns: tuple[str, ...],
    batch_size: int,
    device: str,
) -> pl.DataFrame:
    """Score one split with the persistent Ditto state bound to each source client."""
    selected = _score_input_frame(path, split=split, feature_columns=feature_columns).with_row_index("_score_row")
    chunks: list[pl.DataFrame] = []
    for client, rows in selected.group_by("client_id", maintain_order=True):
        client_id = str(client[0])
        if client_id not in models:
            raise ValueError(f"Personalized checkpoint is unavailable for client '{client_id}'")
        scores = compute_reconstruction_scores(
            models[client_id],
            torch.tensor(rows.select(*feature_columns).to_numpy(), dtype=torch.float32),
            batch_size=batch_size,
            device=device,
        ).numpy()
        chunks.append(rows.with_columns(pl.Series("score", scores)))
    return _score_output_frame(pl.concat(chunks).sort("_score_row").drop("_score_row"), None)
