"""Typed global and personalized reconstruction scoring."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.data.contracts.enums import SplitMembership
from datp_core.learning.checkpoints.codec import (
    ClientModelState,
    ModelState,
    decode_global_state,
    decode_personalized_states,
    load_model_state,
)
from datp_core.learning.contracts.model import BatchingProfile, DenseAutoencoderProfile
from datp_core.learning.model.autoencoder import build_autoencoder
from datp_core.learning.model.runtime import TorchRuntime
from datp_core.learning.scoring.data import MaterializedFrame, score_output_frame, scoring_frame
from datp_core.learning.training.engine import LearningDataError


@dataclass(frozen=True, slots=True)
class GlobalScoringRequest:
    materialization: MaterializedFrame
    split: SplitMembership
    checkpoint_payload: bytes
    selected_round: int
    architecture: DenseAutoencoderProfile
    batching: BatchingProfile
    runtime: TorchRuntime
    model_initialization_seed: int


@dataclass(frozen=True, slots=True)
class PersonalizedScoringRequest:
    materialization: MaterializedFrame
    split: SplitMembership
    personalized_checkpoint_payload: bytes
    selected_round: int
    architecture: DenseAutoencoderProfile
    batching: BatchingProfile
    runtime: TorchRuntime
    model_initialization_seed: int


ScoringRequest = GlobalScoringRequest | PersonalizedScoringRequest


class ReconstructionScoringService:
    def score(self, request: ScoringRequest) -> pl.DataFrame:
        match request:
            case GlobalScoringRequest():
                return self._score_global(request)
            case PersonalizedScoringRequest():
                return self._score_personalized(request)
        raise TypeError("Unsupported scoring request")

    def _score_global(self, request: GlobalScoringRequest) -> pl.DataFrame:
        selected = scoring_frame(request.materialization, request.split)
        state = decode_global_state(request.checkpoint_payload, request.selected_round)
        model = self._model(request, state)
        scores = self._compute_scores(
            model,
            selected.select(*request.materialization.feature_columns).to_numpy(),
            request.batching,
            request.runtime,
        )
        return score_output_frame(selected, scores)

    def _score_personalized(self, request: PersonalizedScoringRequest) -> pl.DataFrame:
        selected = scoring_frame(request.materialization, request.split).with_row_index("_score_row")
        client_ids = tuple(sorted(str(value) for value in selected["client_id"].unique().to_list()))
        states = decode_personalized_states(
            request.personalized_checkpoint_payload,
            request.selected_round,
            client_ids,
        )
        chunks: list[pl.DataFrame] = []
        for key, rows in selected.group_by("client_id", maintain_order=True):
            client_id = str(key[0])
            state = self._client_state(states, client_id)
            model = self._model(request, state)
            scores = self._compute_scores(
                model,
                rows.select(*request.materialization.feature_columns).to_numpy(),
                request.batching,
                request.runtime,
            )
            chunks.append(rows.with_columns(pl.Series("score", scores, dtype=pl.Float64)))
        ordered = pl.concat(chunks).sort("_score_row").drop("_score_row")
        scores = ordered["score"].to_numpy()
        return score_output_frame(ordered.drop("score"), scores)

    @staticmethod
    def _compute_scores(
        model: nn.Module,
        values: np.ndarray,
        batching: BatchingProfile,
        runtime: TorchRuntime,
    ) -> np.ndarray:
        if values.ndim != 2 or values.shape[0] < 1:
            raise LearningDataError("Scoring requires a non-empty two-dimensional feature matrix")
        tensor = torch.as_tensor(values, dtype=runtime.dtype, device="cpu")
        loader = DataLoader(
            TensorDataset(tensor),
            batch_size=int(batching.micro_batch_size),
            shuffle=False,
            drop_last=False,
            num_workers=int(batching.worker_count),
            pin_memory=batching.pin_memory,
            persistent_workers=batching.persistent_workers,
        )
        model = model.to(device=runtime.device, dtype=runtime.dtype)
        model.eval()
        chunks: list[torch.Tensor] = []
        with torch.inference_mode():
            for (batch_inputs,) in loader:
                batch_inputs = batch_inputs.to(
                    device=runtime.device,
                    dtype=runtime.dtype,
                    non_blocking=batching.pin_memory,
                )
                reconstruction = model(batch_inputs)
                chunks.append(torch.mean((reconstruction - batch_inputs) ** 2, dim=1).detach().cpu())
        if not chunks:
            raise LearningDataError("Scoring loader produced no batches")
        return torch.cat(chunks).numpy()

    @staticmethod
    def _client_state(states: tuple[ClientModelState, ...], client_id: str) -> ModelState:
        for state in states:
            if state.client_id == client_id:
                return state.state
        raise LearningDataError(f"Personalized checkpoint is unavailable for client '{client_id}'")

    @staticmethod
    def _model(
        request: GlobalScoringRequest | PersonalizedScoringRequest,
        state: ModelState,
    ) -> nn.Module:
        model = build_autoencoder(
            request.architecture,
            len(request.materialization.feature_columns),
            request.model_initialization_seed,
            request.runtime,
        )
        load_model_state(model, state)
        model.eval()
        return model
