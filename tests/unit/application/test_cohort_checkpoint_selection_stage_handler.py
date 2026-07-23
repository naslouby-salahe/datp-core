"""CohortCheckpointSelectionStageHandler executed against synthetic per-seed selection evidence.

This handler only reads the JSON ``.selection`` evidence each seed's real training run would
have produced (see test_model_training_stage_handler.py for that production path); it does not
care how that evidence was produced, so committing it directly here is a faithful, minimal way
to exercise the actual cross-seed averaging and selection rule with hand-computed expectations.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from datp_core.learning.checkpoints import CohortCheckpointSelectionStageHandler
from datp_core.bootstrap import DatpApplication, build_application
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    BytesPayload,
)
from datp_core.learning.checkpoints import select_cohort_validation_checkpoint
from datp_core.pipeline.identifiers import ExperimentId, RunId
from datp_core.pipeline.models import JobExecutionStatus, StageJob, StageKind
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.experiments.planning import expand_experiment_jobs

_SCHEDULED_ROUNDS = (25, 50, 75, 100, 125, 150, 200)


def _cohort_job_and_run_id(app: DatpApplication) -> tuple[StageJob, RunId]:
    experiment_id = ExperimentId("confirmatory_threshold_scope_effect")
    graph = expand_experiment_jobs(app.config.experiments.get(experiment_id), app.config)
    job = next(item for item in graph.jobs if item.stage is StageKind.CHECKPOINT_SELECTION)
    run_id = RunId(f"run_confirmatory_threshold_scope_effect_{app.config.execution_fingerprint.value[:12]}")
    return job, run_id


def _commit_seed_selection(
    repository: AtomicArtifactRepository,
    app: DatpApplication,
    run_id: RunId,
    dependency_value: str,
    checkpoint_key: ArtifactKey,
    round_losses: list[tuple[int, float]],
) -> None:
    payload = json.dumps({"round_losses": [list(item) for item in round_losses]}).encode("utf-8")
    relative_path = f"runs/{run_id.value}/{dependency_value}.selection"
    selection_key = ArtifactKey(
        artifact_id=ArtifactId(f"{checkpoint_key.artifact_id.value}:selection"), kind=ArtifactKind.CHECKPOINT_SELECTION
    )
    result = repository.commit(_commit_request(app, relative_path, selection_key, payload))
    assert result.success, result.error_message


def _commit_request(
    app: DatpApplication, relative_path: str, artifact_key: ArtifactKey, payload: bytes
) -> ArtifactCommitRequest:
    return ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=artifact_key,
            artifact_format=ArtifactFormat.JSON,
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


def test_cohort_selection_picks_the_round_with_the_lowest_cross_seed_mean_loss(tmp_path: Path) -> None:
    app = build_application()
    job, run_id = _cohort_job_and_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    # Ten distinct, hand-authored loss curves; round 100 has the lowest mean by construction.
    per_seed_losses = [
        [
            (round_number, 1.0 + 0.01 * seed_index + (0.5 if round_number != 100 else 0.05))
            for round_number in _SCHEDULED_ROUNDS
        ]
        for seed_index in range(10)
    ]
    for dependency, checkpoint_key, losses in zip(job.dependencies, job.inputs, per_seed_losses, strict=True):
        _commit_seed_selection(repository, app, run_id, dependency.value, checkpoint_key, losses)

    outcome = CohortCheckpointSelectionStageHandler(app.config, repository).execute(job, run_id)

    assert outcome.status is JobExecutionStatus.SUCCESS
    read = repository.read(f"runs/{run_id.value}/{job.job_id.value}")
    assert read.found and read.payload_bytes is not None
    payload = json.loads(read.payload_bytes)
    expected_round = select_cohort_validation_checkpoint(
        scheduled_rounds=_SCHEDULED_ROUNDS, seed_losses=per_seed_losses
    )
    assert expected_round == 100
    assert payload["selected_round"] == expected_round
    assert payload["seed_round_losses"] == [[list(item) for item in losses] for losses in per_seed_losses]


def test_cohort_selection_reuses_a_frozen_result_without_recomputation(tmp_path: Path) -> None:
    app = build_application()
    job, run_id = _cohort_job_and_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    per_seed_losses = [[(round_number, 1.0) for round_number in _SCHEDULED_ROUNDS] for _ in range(10)]
    for dependency, checkpoint_key, losses in zip(job.dependencies, job.inputs, per_seed_losses, strict=True):
        _commit_seed_selection(repository, app, run_id, dependency.value, checkpoint_key, losses)
    handler = CohortCheckpointSelectionStageHandler(app.config, repository)
    first = handler.execute(job, run_id)
    assert first.status is JobExecutionStatus.SUCCESS
    first_bytes = repository.read(f"runs/{run_id.value}/{job.job_id.value}").payload_bytes

    second = handler.execute(job, run_id)

    assert second.status is JobExecutionStatus.REUSED
    assert repository.read(f"runs/{run_id.value}/{job.job_id.value}").payload_bytes == first_bytes


def test_cohort_selection_fails_typed_when_a_seed_dependency_is_missing_evidence(tmp_path: Path) -> None:
    app = build_application()
    job, run_id = _cohort_job_and_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    # Commit evidence for only the first 9 of 10 seeds -- the last dependency is left unavailable.
    per_seed_losses = [[(round_number, 1.0) for round_number in _SCHEDULED_ROUNDS] for _ in range(9)]
    for dependency, checkpoint_key, losses in zip(job.dependencies[:9], job.inputs[:9], per_seed_losses, strict=True):
        _commit_seed_selection(repository, app, run_id, dependency.value, checkpoint_key, losses)

    outcome = CohortCheckpointSelectionStageHandler(app.config, repository).execute(job, run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message is not None and "unavailable" in outcome.error_message.lower()


def test_cohort_selection_rejects_a_per_seed_job_context(tmp_path: Path) -> None:
    app = build_application()
    job, run_id = _cohort_job_and_run_id(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    per_seed_job = replace(job, context=replace(job.context, seed=0))

    outcome = CohortCheckpointSelectionStageHandler(app.config, repository).execute(per_seed_job, run_id)

    assert outcome.status is JobExecutionStatus.FAILED
    assert (
        outcome.error_message
        == "Checkpoint cohort selection is only valid for the configured primary FedAvg experiment"
    )
