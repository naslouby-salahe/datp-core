"""Typed checkpoint selection rules."""

from __future__ import annotations

from datp_core.learning.contracts.checkpoints import (
    AuthorizedLookupSelection,
    CheckpointProfile,
    FirstQualifyingConvergenceSelection,
    FixedRoundSelection,
    LowestCalibrationLossSelection,
)
from datp_core.learning.contracts.enums import CheckpointTieBreak, NoQualifyingRoundPolicy
from datp_core.learning.training.engine import RoundMetric, TrainingResult


class CheckpointSelectionError(ValueError):
    """Checkpoint selection failed under the resolved profile."""


def select_checkpoint_round(
    profile: CheckpointProfile,
    result: TrainingResult,
    authorized_lookup_round: int | None,
) -> int:
    captured_rounds = tuple(checkpoint.round_number for checkpoint in result.global_checkpoints)
    if captured_rounds != tuple(int(value) for value in profile.capture_rounds):
        raise CheckpointSelectionError("Captured checkpoint rounds do not match the resolved profile")
    selection = profile.selection
    match selection:
        case FixedRoundSelection():
            selected = int(selection.selected_round)
        case LowestCalibrationLossSelection():
            selected = _lowest_loss_round(result.round_metrics, captured_rounds, selection.tie_break)
        case FirstQualifyingConvergenceSelection():
            selected = _first_qualifying_round(
                result.round_metrics,
                int(profile.total_rounds),
                selection,
            )
        case AuthorizedLookupSelection():
            if authorized_lookup_round is None:
                raise CheckpointSelectionError("Authorized lookup selection requires source evidence")
            selected = authorized_lookup_round
        case _:
            raise CheckpointSelectionError("Unsupported checkpoint selection profile")
    if selected not in captured_rounds:
        raise CheckpointSelectionError("Selected checkpoint round was not captured")
    return selected


def _lowest_loss_round(
    metrics: tuple[RoundMetric, ...],
    captured_rounds: tuple[int, ...],
    tie_break: CheckpointTieBreak,
) -> int:
    candidates = tuple(metric for metric in metrics if metric.round_number in captured_rounds)
    if not candidates:
        raise CheckpointSelectionError("No captured round has calibration-loss evidence")
    minimum_loss = min(metric.global_calibration_loss for metric in candidates)
    tied = tuple(metric.round_number for metric in candidates if metric.global_calibration_loss == minimum_loss)
    match tie_break:
        case CheckpointTieBreak.EARLIEST_ROUND:
            return min(tied)
        case CheckpointTieBreak.LATEST_ROUND:
            return max(tied)
    raise CheckpointSelectionError(f"Unsupported checkpoint tie-break '{tie_break.value}'")


def _first_qualifying_round(
    metrics: tuple[RoundMetric, ...],
    round_cap: int,
    selection: FirstQualifyingConvergenceSelection,
) -> int:
    losses = tuple(metric.global_calibration_loss for metric in metrics)
    if len(losses) != round_cap:
        raise CheckpointSelectionError("Convergence selection requires one loss for every training round")
    initial_rounds = int(selection.initial_rounds)
    window_rounds = int(selection.window_rounds)
    tolerance = float(selection.relative_loss_tolerance)
    if initial_rounds >= round_cap:
        raise CheckpointSelectionError("Initial convergence rounds must be below the total round budget")
    if window_rounds >= round_cap:
        raise CheckpointSelectionError("Convergence window must be below the total round budget")
    for round_number in range(max(initial_rounds, window_rounds) + 1, round_cap + 1):
        start_loss = losses[round_number - window_rounds - 1]
        end_loss = losses[round_number - 1]
        denominator = abs(start_loss)
        relative_change = abs(end_loss - start_loss) if denominator == 0.0 else abs(end_loss - start_loss) / denominator
        if relative_change <= tolerance:
            return round_number
    match selection.no_qualifying_round:
        case NoQualifyingRoundPolicy.FINAL_ROUND:
            return round_cap
        case NoQualifyingRoundPolicy.FAIL:
            raise CheckpointSelectionError("No round satisfied the configured convergence rule")
    raise CheckpointSelectionError(
        f"Unsupported no-qualifying-round policy '{selection.no_qualifying_round.value}'"
    )
