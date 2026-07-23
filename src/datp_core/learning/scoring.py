"""Reconstruction scoring: shared and Ditto-personalized, over materialized splits, plus the
score-generation pipeline stage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import polars as pl
import torch
import torch.nn as nn
from safetensors.torch import load as load_safetensors
from torch.utils.data import DataLoader, TensorDataset

from datp_core.artifacts.models import (
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.datasets.models import SplitMethod
from datp_core.experiments.identity import IdentityBuilder, execution_run_id
from datp_core.learning.autoencoder import DynamicDenseAutoencoder, require_cuda_training_device
from datp_core.learning.models import CheckpointAuthorization, PersonalizationStrategy
from datp_core.pipeline.frames import validate_calibration_score_frame, validate_test_score_frame
from datp_core.pipeline.identifiers import DatasetId, RunId
from datp_core.pipeline.models import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact

_SCORE_IDENTITY_COLUMNS = ("source_path", "source_row_index", "client_id", "split", "is_attack")


def load_benign_client_tensors(
    path: Path, split: str, feature_columns: tuple[str, ...]
) -> tuple[tuple[str, torch.Tensor], ...]:
    """Load configured benign rows for one authorized split, ordered by client."""
    if not feature_columns:
        raise ValueError("Training requires configured model feature columns")
    frame = pl.read_parquet(path, columns=["split", "client_id", "is_attack", *feature_columns])
    required = {"split", "client_id", "is_attack", *feature_columns}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Materialized payload lacks training columns: {', '.join(missing)}")
    selected = frame.filter((pl.col("split") == split) & ~pl.col("is_attack")).select("client_id", *feature_columns)
    if selected.is_empty():
        raise ValueError(f"Materialized payload has no benign {split} rows")
    tensors: list[tuple[str, torch.Tensor]] = []
    for client_id, client_rows in selected.group_by("client_id", maintain_order=True):
        values = client_rows.select(*feature_columns).to_numpy()
        if not np.isfinite(values).all():
            raise ValueError(f"Benign {split} rows for client '{client_id[0]}' contain non-finite feature values")
        tensors.append((str(client_id[0]), torch.tensor(values, dtype=torch.float32)))
    return tuple(sorted(tensors, key=lambda item: item[0]))


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


def _score_input_frame(path: Path, *, split: str, feature_columns: tuple[str, ...]) -> pl.DataFrame:
    if split not in {"calibration", "test", "historical_calibration", "future_recalibration", "future_evaluation"}:
        raise ValueError(f"Scoring does not authorize split '{split}'")
    frame = pl.read_parquet(path, columns=[*_SCORE_IDENTITY_COLUMNS, *feature_columns])
    selected = frame.filter(pl.col("split") == split)
    if selected.is_empty():
        raise ValueError(f"Materialized payload has no {split} rows to score")
    if split in {"calibration", "historical_calibration", "future_recalibration"} and selected["is_attack"].any():
        raise ValueError("Calibration scoring must not include attack rows")
    if selected.select(pl.struct("source_path", "source_row_index").is_duplicated().any()).item():
        raise ValueError("Score input contains duplicate row identities")
    if not np.isfinite(selected.select(*feature_columns).to_numpy()).all():
        raise ValueError("Score input contains non-finite feature values")
    return selected


def _score_output_frame(selected: pl.DataFrame, scores: np.ndarray | None) -> pl.DataFrame:
    if scores is not None:
        selected = selected.with_columns(pl.Series("score", scores, dtype=pl.Float64))
    scores = selected["score"].to_numpy()
    if not np.isfinite(scores).all() or (scores < 0.0).any():
        raise ValueError("Model produced non-finite or negative reconstruction scores")
    return (
        selected.select(*_SCORE_IDENTITY_COLUMNS, "score")
        .with_columns(
            pl.col("score").cast(pl.Float64),
            pl.col("is_attack").cast(pl.Int64).alias("label"),
        )
        .drop("is_attack")
    )


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


def materialized_feature_columns(path: Path) -> tuple[str, ...]:
    """Infer model feature columns from a materialized Parquet file's schema.

    Shared by `learning/training.py` (materialization has no configured `field_schema.model_features`
    fallback path) and this module's own `ScoreGenerationStageHandler`.
    """
    metadata_columns = {"split", "client_id", "source_path", "source_row_index", "is_attack", "chronology_key"}
    columns = tuple(column for column in pl.read_parquet(path, n_rows=0).columns if column not in metadata_columns)
    if not columns:
        raise ValueError("Materialized dataset has no model feature columns")
    return columns


def _score_split(kind: ArtifactKind, context: StageJobContext, config: ResolvedProjectConfiguration) -> str | None:
    experiment = config.experiments.get(context.experiment_id)
    population = config.populations.get(context.population_id or experiment.population_ids[0])
    dataset = config.datasets.get(population.dataset_id)
    setup = dataset.setup(population.setup_id)
    materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
    temporal = materialization.split_method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL
    if kind is ArtifactKind.CALIBRATION_SCORES:
        return "historical_calibration" if temporal else "calibration"
    if kind is ArtifactKind.FUTURE_RECALIBRATION_SCORES:
        return "future_recalibration" if temporal else None
    if kind is ArtifactKind.TEST_SCORES:
        return "future_evaluation" if temporal else "test"
    return None


def _load_checkpoint_model(
    states: Mapping[str, object], prefix: str, input_dimension: int, hidden_dims: tuple[int, ...]
) -> DynamicDenseAutoencoder:
    state = {name.removeprefix(prefix): tensor for name, tensor in states.items() if name.startswith(prefix)}
    if not state:
        raise ValueError("Selected checkpoint is absent from the persisted checkpoint grid")
    model = DynamicDenseAutoencoder(input_dimension, hidden_dims)
    model.load_state_dict(state)
    model.eval()
    return model


class ScoreGenerationStageHandler:
    """Score one authorized materialized split from its selected model checkpoint."""

    stage = StageKind.SCORE_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        split = _score_split(job.output.kind, job.context, self._config)
        if split is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Unknown score artifact kind"
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        training_path = f"runs/{run_id.value}/{IdentityBuilder.training_job_id(job.context).value}"
        selection_path, selection_key = self._selection_location(job, run_id, profile.checkpoint_authorization)
        selection = self._repository.read(selection_path)
        if not self._repository.assess_reuse(
            selection_path,
            selection_key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Selected-checkpoint evidence is unavailable or incompatible",
            )
        if not selection.found or selection.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Selected-checkpoint evidence is unreadable"
            )
        checkpoint = self._repository.read(training_path)
        personalized_key = IdentityBuilder.personalized_checkpoint_key(job.context)
        personalized_path = f"{training_path}.personalized"
        personalized = (
            self._repository.read(personalized_path)
            if profile.personalization == PersonalizationStrategy.DITTO
            else None
        )
        materialization = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.materialization_job_id(job.context).value}"
        )
        if not checkpoint.found or checkpoint.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Model checkpoint is unavailable"
            )
        if not materialization.found or materialization.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Materialization artifact is unavailable"
            )
        if profile.personalization == PersonalizationStrategy.DITTO and (
            not self._repository.assess_reuse(
                personalized_path,
                personalized_key,
                self._config.scientific_fingerprint,
                self._config.execution_fingerprint,
            ).can_reuse
            or personalized is None
            or not personalized.found
            or personalized.payload_bytes is None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Personalized checkpoint is unavailable or incompatible",
            )
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        features = dataset.field_schema.model_features
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            if self._config.runtime.active_execution_profile.device_policy != "cuda_required":
                raise ValueError("Score generation requires the configured CUDA-required execution profile")
            with TemporaryDirectory(prefix="datp_scoring_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization.payload_bytes)
                feature_columns = (
                    features.order if features is not None else materialized_feature_columns(materialized_path)
                )
                selected_round = json.loads(selection.payload_bytes)["selected_round"]
                if profile.personalization == PersonalizationStrategy.DITTO:
                    assert personalized is not None and personalized.payload_bytes is not None
                    all_states = load_safetensors(personalized.payload_bytes)
                    models = {
                        client_id: _load_checkpoint_model(
                            all_states,
                            f"round_{selected_round}.client_{client_id}.",
                            len(feature_columns),
                            tuple(int(value.value) for value in architecture.hidden_dims),
                        )
                        for client_id in pl.read_parquet(materialized_path, columns=["client_id"])["client_id"]
                        .unique()
                        .sort()
                    }
                    scores = score_personalized_materialized_split(
                        models,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                else:
                    model = _load_checkpoint_model(
                        load_safetensors(checkpoint.payload_bytes),
                        f"round_{selected_round}.",
                        len(feature_columns),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_materialized_split(
                        model,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                scores = scores.with_columns(
                    pl.lit(
                        personalized_key.artifact_id.value
                        if profile.personalization == PersonalizationStrategy.DITTO
                        else job.inputs[0].artifact_id.value
                    ).alias("checkpoint_artifact_id"),
                    pl.lit(job.context.seed).alias("seed"),
                    pl.lit("higher_score_means_more_anomalous").alias("score_orientation"),
                )
        except (OSError, RuntimeError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        validated = (
            validate_calibration_score_frame(scores)
            if job.output.kind
            in {
                ArtifactKind.CALIBRATION_SCORES,
                ArtifactKind.FUTURE_RECALIBRATION_SCORES,
            }
            else validate_test_score_frame(scores)
        )
        payload = BytesIO()
        validated.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(
                self._config,
                (
                    *job.inputs,
                    selection_key,
                    *((personalized_key,) if profile.personalization == PersonalizationStrategy.DITTO else ()),
                ),
            ),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message=commit.error_message or "score artifact commit failed"
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _selection_location(
        self, job: StageJob, run_id: RunId, authorization: CheckpointAuthorization
    ) -> tuple[str, ArtifactKey]:
        if authorization == CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE:
            selection_context = StageJobContext(experiment_id=job.context.experiment_id)
            return (
                f"runs/{run_id.value}/{IdentityBuilder.cohort_checkpoint_selection_job_id(selection_context).value}",
                IdentityBuilder.cohort_checkpoint_selection_key(selection_context),
            )
        if authorization == CheckpointAuthorization.LOOKUP_OF_FEDERATED_AVERAGING:
            source = self._config.primary_federated_checkpoint_experiment()
            selection_context = StageJobContext(experiment_id=source.identifier)
            source_run_id = execution_run_id(source.identifier, self._config.execution_fingerprint.value)
            return (
                f"runs/{source_run_id.value}/{IdentityBuilder.cohort_checkpoint_selection_job_id(selection_context).value}",
                IdentityBuilder.cohort_checkpoint_selection_key(selection_context),
            )
        selection_key = ArtifactKey(
            artifact_id=ArtifactId(f"{job.inputs[0].artifact_id.value}:selection"),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )
        return (f"runs/{run_id.value}/{IdentityBuilder.training_job_id(job.context).value}.selection", selection_key)
