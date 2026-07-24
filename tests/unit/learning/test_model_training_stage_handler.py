"""ModelTrainingStageHandler executed against a real, tiny synthetic materialized dataset.

Uses the real, unmodified anchor_reproduction experiment configuration (115 real N-BaIoT
feature columns, its real 150-round checkpoint grid and convergence-based selection rule) so
the test exercises the actual scientific selection rule, not a stand-in.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import torch
from _synthetic_training_fixtures import build_synthetic_materialized_frame, commit_materialized_dataset
from safetensors.torch import load as load_safetensors

from datp_core.app import DatpApplication, build_application
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.learning.checkpoints import select_anchor_checkpoint_round
from datp_core.learning.training import ModelTrainingStageHandler
from datp_core.pipeline.models import JobExecutionStatus, StageJob, StageKind


def _anchor_training_job(app: DatpApplication, seed: int = 0) -> StageJob:
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    return next(job for job in graph.jobs if job.stage is StageKind.MODEL_TRAINING and job.context.seed == seed)


def _anchor_run_id(app: DatpApplication) -> RunId:
    return RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")


def _commit_synthetic_materialization(
    app: DatpApplication, repository: AtomicArtifactRepository, job: StageJob
) -> None:
    assert job.context.population_id is not None
    dataset = app.config.datasets[app.config.populations.get(job.context.population_id).dataset_id]
    assert dataset.field_schema.model_features is not None
    feature_columns = dataset.field_schema.model_features.order
    frame = build_synthetic_materialized_frame(feature_columns)
    commit_materialized_dataset(
        repository,
        app.config,
        run_id_value=_anchor_run_id(app).value,
        job_id_value=IdentityBuilder.materialization_job_id(job.context).value,
        output_key=job.inputs[0],
        frame=frame,
    )


@pytest.mark.skipif(not torch.cuda.is_available(), reason="cuda_required profile forbids CPU fallback")
def test_model_training_produces_a_checkpoint_selected_by_the_anchor_convergence_rule(tmp_path: Path) -> None:
    app = build_application()
    job = _anchor_training_job(app)
    experiment = app.config.experiments.get(ExperimentId("anchor_reproduction"))
    run_id = _anchor_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    _commit_synthetic_materialization(app, repository, job)

    outcome = ModelTrainingStageHandler(app.config, repository).execute(job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    assert outcome.produced_artifact == job.output

    checkpoint_read = repository.read(f"runs/{run_id.value}/{job.job_id.value}")
    assert checkpoint_read.found and checkpoint_read.payload_bytes is not None
    checkpoint_states = load_safetensors(checkpoint_read.payload_bytes)
    recorded_rounds = sorted({int(name.split(".", 1)[0].removeprefix("round_")) for name in checkpoint_states})
    checkpoint_profile = app.config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
    assert recorded_rounds == [int(value.value) for value in checkpoint_profile.selected_rounds]

    selection_read = repository.read(f"runs/{run_id.value}/{job.job_id.value}.selection")
    assert selection_read.found and selection_read.payload_bytes is not None
    selection = json.loads(selection_read.payload_bytes)
    assert len(selection["round_losses"]) == 150
    assert checkpoint_profile.convergence is not None
    assert checkpoint_profile.total_rounds is not None
    expected_round = select_anchor_checkpoint_round(
        convergence=checkpoint_profile.convergence,
        recorded_losses=[tuple(item) for item in selection["round_losses"]],
        round_cap=int(checkpoint_profile.total_rounds.value),
    )
    assert selection["selected_round"] == expected_round
    assert expected_round in recorded_rounds
    assert selection["model_initialization_seed"] is not None
    assert len(selection["dataloader_shuffle_seeds"]) > 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="cuda_required profile forbids CPU fallback")
def test_model_training_reuses_a_frozen_checkpoint_without_retraining(tmp_path: Path) -> None:
    app = build_application()
    job = _anchor_training_job(app)
    run_id = _anchor_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    _commit_synthetic_materialization(app, repository, job)
    handler = ModelTrainingStageHandler(app.config, repository)
    first = handler.execute(job, run_id)
    assert first.status is JobExecutionStatus.SUCCESS
    checkpoint_bytes_after_first_run = repository.read(f"runs/{run_id.value}/{job.job_id.value}").payload_bytes

    second = handler.execute(job, run_id)

    assert second.status is JobExecutionStatus.REUSED
    assert second.produced_artifact == job.output
    checkpoint_bytes_after_second_call = repository.read(f"runs/{run_id.value}/{job.job_id.value}").payload_bytes
    assert checkpoint_bytes_after_second_call == checkpoint_bytes_after_first_run


def test_model_training_fails_typed_when_materialization_is_unavailable(tmp_path: Path) -> None:
    app = build_application()
    job = _anchor_training_job(app)
    run_id = _anchor_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)

    outcome = ModelTrainingStageHandler(app.config, repository).execute(job, run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message == "Materialization artifact is unavailable"


def test_model_training_rejects_a_fedprox_coefficient_on_plain_fedavg(tmp_path: Path) -> None:
    app = build_application()
    job = _anchor_training_job(app)
    contaminated_job = replace(job, context=replace(job.context, federated_proximal_mu=0.5))
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    run_id = _anchor_run_id(app)

    outcome = ModelTrainingStageHandler(app.config, repository).execute(contaminated_job, run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message == "FedAvg training must not carry a FedProx coefficient"
