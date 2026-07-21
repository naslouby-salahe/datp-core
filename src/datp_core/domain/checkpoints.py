"""Pure resolved anchor terminal-checkpoint selection rule.

Implements the historical convergence rule declared for the ``anchor_terminal_round``
checkpoint profile: select the first recorded round at or after ``rounds_initial`` whose
trailing-window relative loss change is below ``tolerance``; otherwise the round cap.
"""

from __future__ import annotations

from collections.abc import Sequence

from datp_core.domain.catalogue import CheckpointConvergenceRecord


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
        if window_start_loss == 0.0:
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
