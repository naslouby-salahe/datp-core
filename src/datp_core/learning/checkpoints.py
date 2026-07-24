"""Pure anchor/cohort checkpoint-selection algorithms, and the checkpoint-selection pipeline stage.

Implements the historical convergence rule declared for the ``anchor_terminal_round``
checkpoint profile: select the first recorded round at or after ``rounds_initial`` whose
trailing-window relative loss change is below ``tolerance``; otherwise the round cap.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass

from datp_core.artifacts.models import (
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import RunId
from datp_core.experiments.identity import IdentityBuilder, execution_run_id
from datp_core.learning.models import (
    CheckpointAuthorization,
    CheckpointConvergenceRecord,
    PersonalizationStrategy,
    TrainingProfileKind,
)
from datp_core.pipeline.execution import artifact_parents, commit_artifact
from datp_core.pipeline.models import StageJob, StageJobContext, StageJobOutcome, StageKind


def select_anchor_checkpoint_round(
    *,
    convergence: CheckpointConvergenceRecord,
    recorded_losses: Sequence[tuple[int, float]],
    round_cap: int,
) -> int:
    """Select the anchor terminal-checkpoint round.

    ``recorded_losses`` is an ordered sequence of ``(round_number, loss)`` pairs, one per
    recorded round in ascending round order. The trailing window spans
    ``convergence.window_rounds`` recorded rounds. For the round at recorded position ``i``
    the window start loss is the recorded round ``window_rounds - 1`` positions earlier.

    The relative change is ``abs(window_start_loss - loss) / abs(window_start_loss)``. When
    the window start loss is exactly zero the relative change is treated as zero
    (``zero_start_loss_behavior``). The first round at or after ``rounds_initial`` with a
    relative change strictly below ``tolerance`` qualifies; if none qualifies the
    ``round_cap`` is returned (``no_qualifying_round_behavior``).
    """
    losses = tuple(recorded_losses)
    window = convergence.window_rounds.value
    tolerance = convergence.tolerance.value
    minimum_round = convergence.rounds_initial.value
    for position, (round_number, loss_value) in enumerate(losses):
        if position < window - 1:
            continue
        if round_number < minimum_round:
            continue
        window_start_loss = losses[position - (window - 1)][1]
        if math.isclose(window_start_loss, 0.0, abs_tol=0.0):
            relative_change = 0.0
        else:
            relative_change = abs(window_start_loss - loss_value) / abs(window_start_loss)
        if relative_change < tolerance:
            return round_number
    return round_cap


def select_lowest_validation_loss_checkpoint(
    *, scheduled_rounds: Sequence[int], recorded_losses: Sequence[tuple[int, float]]
) -> int:
    """Select the lowest authorized benign validation loss, breaking ties by earliest round."""
    schedule = tuple(scheduled_rounds)
    if not schedule or len(set(schedule)) != len(schedule) or any(round_number < 1 for round_number in schedule):
        raise ValueError("Checkpoint selection requires unique positive scheduled rounds")
    losses = dict(recorded_losses)
    missing = tuple(round_number for round_number in schedule if round_number not in losses)
    if missing:
        raise ValueError(f"Checkpoint selection is missing scheduled losses: {', '.join(map(str, missing))}")
    return min(schedule, key=lambda round_number: (losses[round_number], round_number))


def select_cohort_validation_checkpoint(
    *, scheduled_rounds: Sequence[int], seed_losses: Sequence[Sequence[tuple[int, float]]]
) -> int:
    """Select one authorized round from the arithmetic mean benign calibration loss over all seeds."""
    if not seed_losses:
        raise ValueError("Cohort checkpoint selection requires at least one seed loss curve")
    schedule = tuple(scheduled_rounds)
    per_seed = tuple(dict(losses) for losses in seed_losses)
    if any(any(round_number not in losses for round_number in schedule) for losses in per_seed):
        raise ValueError("Cohort checkpoint selection is missing a scheduled calibration loss")
    averaged = tuple(
        (round_number, sum(losses[round_number] for losses in per_seed) / len(per_seed)) for round_number in schedule
    )
    return select_lowest_validation_loss_checkpoint(scheduled_rounds=schedule, recorded_losses=averaged)


@dataclass(frozen=True, slots=True)
class _TrainingCheckpointSelection:
    round_losses: tuple[tuple[int, float], ...]
    personalized_round_losses: tuple[tuple[int, float], ...] | None


class CohortCheckpointSelectionStageHandler:
    """Freeze the sole confirmatory FedAvg checkpoint chosen from all seed calibration curves."""

    stage = StageKind.CHECKPOINT_SELECTION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        if profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
            return self._execute_federated_proximal(job, run_id)
        if profile.personalization == PersonalizationStrategy.DITTO:
            return self._execute_ditto(job, run_id)
        if (
            profile.checkpoint_authorization != CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE
            or experiment != self._config.primary_federated_checkpoint_experiment()
            or job.context.seed is not None
            or len(job.inputs) != len(job.dependencies)
            or not job.inputs
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Checkpoint cohort selection is only valid for the configured primary FedAvg experiment",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

        selection_keys = tuple(
            ArtifactKey(
                artifact_id=ArtifactId(f"{checkpoint.artifact_id.value}:selection"),
                kind=ArtifactKind.CHECKPOINT_SELECTION,
            )
            for checkpoint in job.inputs
        )
        try:
            selections = tuple(
                self._read_training_selection(run_id, dependency, selection_key)
                for dependency, selection_key in zip(job.dependencies, selection_keys, strict=True)
            )
            checkpoint_profile = self._config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
            scheduled_rounds = tuple(int(round_number.value) for round_number in checkpoint_profile.selected_rounds)
            seed_losses = tuple(selection.round_losses for selection in selections)
            selected_round = select_cohort_validation_checkpoint(
                scheduled_rounds=scheduled_rounds,
                seed_losses=seed_losses,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = json.dumps(
            {
                "schema_version": 1,
                "selected_round": selected_round,
                "scheduled_rounds": scheduled_rounds,
                "seed_round_losses": [selection.round_losses for selection in selections],
                "selector": checkpoint_profile.selection.rule,
                "aggregation": checkpoint_profile.selection.aggregation,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, (*job.inputs, *selection_keys)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "checkpoint cohort selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _execute_federated_proximal(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        if profile.mu_grid is None or job.context.seed is not None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="FedProx coefficient selection requires its configured coefficient grid",
            )
        expected_contexts = tuple(
            StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                federated_proximal_mu=proximal_mu,
            )
            for seed in cohort.training_seeds
            for proximal_mu in profile.mu_grid
        )
        expected_dependencies = tuple(IdentityBuilder.training_job_id(context) for context in expected_contexts)
        if job.dependencies != expected_dependencies or len(job.inputs) != len(expected_contexts):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="FedProx coefficient selection does not depend on the exact configured training grid",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        try:
            primary_round, primary_key = self._primary_round()
            means = tuple(
                (
                    proximal_mu,
                    self._mean_federated_proximal_loss(
                        run_id, experiment.identifier, cohort.training_seeds, proximal_mu, primary_round
                    ),
                )
                for proximal_mu in profile.mu_grid
            )
        except (KeyError, TypeError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        selection_keys = tuple(self._training_selection_key(context) for context in expected_contexts)
        payload = json.dumps(
            {
                "schema_version": 1,
                "selected_proximal_mu": min(means, key=lambda item: (item[1], item[0]))[0],
                "locked_primary_round": primary_round,
                "mean_benign_calibration_loss_by_mu": means,
                "selector": (
                    "lowest_natural_device_regime_benign_validation_reconstruction_error_at_the_locked_primary_round"
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, (*job.inputs, *selection_keys, primary_key)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "FedProx coefficient selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _execute_ditto(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        if (
            experiment != self._config.primary_ditto_selection_experiment()
            or profile.personalization_parameter_grid is None
            or job.context.seed is not None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Ditto weight selection is only valid for the configured natural-device grid",
            )
        contexts = tuple(
            StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                ditto_proximal_weight=weight,
            )
            for seed in cohort.training_seeds
            for weight in profile.personalization_parameter_grid
        )
        if job.dependencies != tuple(IdentityBuilder.training_job_id(context) for context in contexts):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Ditto weight selection does not depend on the exact configured training grid",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        try:
            primary_round, primary_key = self._primary_round()
            means = tuple(
                (
                    weight,
                    self._mean_ditto_personalized_loss(
                        run_id, experiment.identifier, cohort.training_seeds, weight, primary_round
                    ),
                )
                for weight in profile.personalization_parameter_grid
            )
        except (KeyError, TypeError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        selection_keys = tuple(self._training_selection_key(context) for context in contexts)
        payload = json.dumps(
            {
                "schema_version": 1,
                "selected_ditto_proximal_weight": min(means, key=lambda item: (item[1], item[0]))[0],
                "locked_primary_round": primary_round,
                "mean_benign_calibration_loss_by_weight": means,
                "selector": (
                    "lowest_natural_device_regime_benign_validation_reconstruction_error_at_locked_global_checkpoint"
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, (*job.inputs, *selection_keys, primary_key)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "Ditto weight selection commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _mean_ditto_personalized_loss(
        self, run_id: RunId, experiment_id, seeds, weight: float, selected_round: int
    ) -> float:
        losses = tuple(
            self._personalized_loss_at_round(
                self._read_training_selection(
                    run_id,
                    IdentityBuilder.training_job_id(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            ditto_proximal_weight=weight,
                        )
                    ),
                    self._training_selection_key(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            ditto_proximal_weight=weight,
                        )
                    ),
                ),
                selected_round,
            )
            for seed in seeds
        )
        return sum(losses) / len(losses)

    @staticmethod
    def _personalized_loss_at_round(selection: _TrainingCheckpointSelection, selected_round: int) -> float:
        if selection.personalized_round_losses is None:
            raise ValueError("Ditto training selection evidence lacks personalized calibration losses")
        return dict(selection.personalized_round_losses)[selected_round]

    def _mean_federated_proximal_loss(
        self, run_id: RunId, experiment_id, seeds, proximal_mu: float, selected_round: int
    ) -> float:
        losses = tuple(
            dict(
                self._read_training_selection(
                    run_id,
                    IdentityBuilder.training_job_id(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            federated_proximal_mu=proximal_mu,
                        )
                    ),
                    self._training_selection_key(
                        StageJobContext(
                            experiment_id=experiment_id,
                            seed=int(seed.value),
                            federated_proximal_mu=proximal_mu,
                        )
                    ),
                ).round_losses
            )[selected_round]
            for seed in seeds
        )
        return sum(losses) / len(losses)

    @staticmethod
    def _training_selection_key(context: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=ArtifactId(f"{IdentityBuilder.checkpoint_artifact_id(context).value}:selection"),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )

    def _read_training_selection(
        self, run_id: RunId, dependency, selection_key: ArtifactKey
    ) -> _TrainingCheckpointSelection:
        relative_path = f"runs/{run_id.value}/{dependency.value}.selection"
        if not self._repository.assess_reuse(
            relative_path,
            selection_key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError(f"Training checkpoint-selection evidence is unavailable for '{dependency.value}'")
        selection = self._repository.read(relative_path)
        if not selection.found or selection.payload_bytes is None:
            raise ValueError(f"Training checkpoint-selection evidence is unreadable for '{dependency.value}'")
        parsed = json.loads(selection.payload_bytes)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("round_losses"), list):
            raise ValueError(f"Training checkpoint-selection evidence is malformed for '{dependency.value}'")
        return _TrainingCheckpointSelection(
            round_losses=self._losses_from_payload(parsed["round_losses"], dependency),
            personalized_round_losses=(
                self._losses_from_payload(parsed["personalized_round_losses"], dependency)
                if isinstance(parsed.get("personalized_round_losses"), list)
                else None
            ),
        )

    @staticmethod
    def _losses_from_payload(items: list[object], dependency) -> tuple[tuple[int, float], ...]:
        round_losses: list[tuple[int, float]] = []
        for item in items:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], int)
                or not isinstance(item[1], (int, float))
            ):
                raise ValueError(f"Training checkpoint-selection evidence is malformed for '{dependency.value}'")
            round_losses.append((item[0], float(item[1])))
        return tuple(round_losses)

    def _primary_round(self) -> tuple[int, ArtifactKey]:
        source = self._config.primary_federated_checkpoint_experiment()
        context = StageJobContext(experiment_id=source.identifier)
        key = IdentityBuilder.cohort_checkpoint_selection_key(context)
        source_run_id = execution_run_id(source.identifier, self._config.execution_fingerprint.value)
        relative_path = (
            f"runs/{source_run_id.value}/{IdentityBuilder.cohort_checkpoint_selection_job_id(context).value}"
        )
        if not self._repository.assess_reuse(
            relative_path,
            key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError("The frozen primary FedAvg checkpoint selection is unavailable")
        selection = self._repository.read(relative_path)
        if not selection.found or selection.payload_bytes is None:
            raise ValueError("The frozen primary FedAvg checkpoint selection is unreadable")
        parsed = json.loads(selection.payload_bytes)
        selected_round = parsed.get("selected_round") if isinstance(parsed, dict) else None
        if not isinstance(selected_round, int):
            raise ValueError("The frozen primary FedAvg checkpoint selection is malformed")
        return (selected_round, key)
