"""ScoreGenerationStageHandler executed against a real checkpoint and a hand-verified score.

Uses a checkpoint built with known, deterministic weights so at least one persisted score can
be independently recomputed in the test via the exact reconstruction-error formula
(mean squared error between input and reconstruction), rather than merely checking that scoring
did not raise.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest
import torch
from _synthetic_training_fixtures import (
    build_single_round_checkpoint,
    build_synthetic_materialized_frame,
    commit_materialized_dataset,
)

from datp_core.app import DatpApplication, build_application
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    BytesPayload,
)
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.learning.autoencoder import DynamicDenseAutoencoder
from datp_core.learning.scoring import ScoreGenerationStageHandler
from datp_core.pipeline.models import JobExecutionStatus, StageJob, StageKind

_ROUND = 1


def _score_jobs(app: DatpApplication, seed: int = 0) -> tuple[StageJob, StageJob]:
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    calibration_job = next(
        job
        for job in graph.jobs
        if job.stage is StageKind.SCORE_GENERATION
        and job.context.seed == seed
        and job.output.kind is ArtifactKind.CALIBRATION_SCORES
    )
    test_job = next(
        job
        for job in graph.jobs
        if job.stage is StageKind.SCORE_GENERATION
        and job.context.seed == seed
        and job.output.kind is ArtifactKind.TEST_SCORES
    )
    return calibration_job, test_job


def _run_id(app: DatpApplication) -> RunId:
    return RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")


def _commit(
    app: DatpApplication,
    repository: AtomicArtifactRepository,
    relative_path: str,
    key: ArtifactKey,
    artifact_format: ArtifactFormat,
    payload: bytes,
) -> None:
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=key,
                artifact_format=artifact_format,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=payload),
        )
    )
    assert result.success, result.error_message


def _prepare(
    tmp_path: Path,
) -> tuple[
    DatpApplication, AtomicArtifactRepository, RunId, StageJob, StageJob, tuple[str, ...], DynamicDenseAutoencoder
]:
    app = build_application()
    calibration_job, test_job = _score_jobs(app)
    run_id = _run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    assert calibration_job.context.population_id is not None
    dataset = app.config.datasets[app.config.populations.get(calibration_job.context.population_id).dataset_id]
    assert dataset.field_schema.model_features is not None
    feature_columns = dataset.field_schema.model_features.order
    frame = build_synthetic_materialized_frame(feature_columns)
    commit_materialized_dataset(
        repository,
        app.config,
        run_id_value=run_id.value,
        job_id_value=IdentityBuilder.materialization_job_id(calibration_job.context).value,
        output_key=calibration_job.inputs[1],
        frame=frame,
    )
    experiment = app.config.experiments.get(ExperimentId("anchor_reproduction"))
    profile = app.config.training_profiles.get(experiment.training_profile_id)
    architecture = app.config.model_architectures.get(profile.model_architecture_id)
    hidden_dims = tuple(int(value.value) for value in architecture.hidden_dims)
    checkpoint_bytes, model = build_single_round_checkpoint(feature_columns, hidden_dims, round_number=_ROUND, seed=7)
    training_job_id = IdentityBuilder.training_job_id(calibration_job.context)
    checkpoint_key = calibration_job.inputs[0]
    _commit(
        app,
        repository,
        f"runs/{run_id.value}/{training_job_id.value}",
        checkpoint_key,
        ArtifactFormat.SAFETENSORS,
        checkpoint_bytes,
    )
    selection_key = ArtifactKey(
        artifact_id=ArtifactId(f"{checkpoint_key.artifact_id.value}:selection"), kind=ArtifactKind.CHECKPOINT_SELECTION
    )
    _commit(
        app,
        repository,
        f"runs/{run_id.value}/{training_job_id.value}.selection",
        selection_key,
        ArtifactFormat.JSON,
        json.dumps({"selected_round": _ROUND}).encode("utf-8"),
    )
    return app, repository, run_id, calibration_job, test_job, feature_columns, model


@pytest.mark.skipif(not torch.cuda.is_available(), reason="cuda_required profile forbids CPU fallback")
def test_calibration_scores_exclude_attack_rows_and_preserve_row_identity(tmp_path: Path) -> None:
    app, repository, run_id, calibration_job, _test_job, _feature_columns, _model = _prepare(tmp_path)

    outcome = ScoreGenerationStageHandler(app.config, repository).execute(calibration_job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    read = repository.read(f"runs/{run_id.value}/{calibration_job.job_id.value}")
    assert read.found and read.payload_bytes is not None
    scores = pl.read_parquet(read.payload_bytes)
    assert scores.height == 12  # 2 clients x 6 benign calibration rows each; no attack rows exist in calibration
    assert set(scores["client_id"].unique().to_list()) == {"client_a", "client_b"}
    assert scores["source_row_index"].is_duplicated().sum() == 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="cuda_required profile forbids CPU fallback")
def test_test_scores_hand_verified_reconstruction_error_and_labels(tmp_path: Path) -> None:
    app, repository, run_id, _calibration_job, test_job, feature_columns, model = _prepare(tmp_path)

    outcome = ScoreGenerationStageHandler(app.config, repository).execute(test_job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    read = repository.read(f"runs/{run_id.value}/{test_job.job_id.value}")
    assert read.found and read.payload_bytes is not None
    scores = pl.read_parquet(read.payload_bytes)
    assert scores.height == 12  # 2 clients x (3 benign + 3 attack) test rows each
    assert set(scores["label"].unique().to_list()) == {0, 1}
    assert scores["score_orientation"].unique().to_list() == ["higher_score_means_more_anomalous"]

    reference_frame = build_synthetic_materialized_frame(feature_columns)
    one_row = scores.row(0, named=True)
    matching_source = next(
        row
        for row in reference_frame.to_dicts()
        if row["source_path"] == one_row["source_path"] and row["source_row_index"] == one_row["source_row_index"]
    )
    input_vector = np.array([matching_source[name] for name in feature_columns], dtype=np.float32)
    with torch.no_grad():
        reconstruction = model(torch.tensor(input_vector).unsqueeze(0)).squeeze(0).numpy()
    expected_score = float(np.mean((reconstruction - input_vector) ** 2))
    assert one_row["score"] == pytest.approx(expected_score)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="cuda_required profile forbids CPU fallback")
def test_score_generation_reuses_a_frozen_score_artifact(tmp_path: Path) -> None:
    app, repository, run_id, calibration_job, _test_job, _feature_columns, _model = _prepare(tmp_path)
    handler = ScoreGenerationStageHandler(app.config, repository)
    first = handler.execute(calibration_job, run_id)
    assert first.status is JobExecutionStatus.SUCCESS
    first_bytes = repository.read(f"runs/{run_id.value}/{calibration_job.job_id.value}").payload_bytes

    second = handler.execute(calibration_job, run_id)

    assert second.status is JobExecutionStatus.REUSED
    assert repository.read(f"runs/{run_id.value}/{calibration_job.job_id.value}").payload_bytes == first_bytes


def test_score_generation_fails_typed_when_checkpoint_is_unavailable(tmp_path: Path) -> None:
    app = build_application()
    calibration_job, _test_job = _score_jobs(app)
    run_id = _run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)

    outcome = ScoreGenerationStageHandler(app.config, repository).execute(calibration_job, run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message == "Selected-checkpoint evidence is unavailable or incompatible"
