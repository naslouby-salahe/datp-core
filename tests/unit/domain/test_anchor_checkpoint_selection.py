"""Anchor terminal-checkpoint selection-rule tests."""

from datp_core.config.resolver import resolve_project_configuration
from datp_core.domain.catalogue import CheckpointConvergenceRecord
from datp_core.domain.checkpoints import (
    select_anchor_checkpoint_round,
    select_cohort_validation_checkpoint,
    select_lowest_validation_loss_checkpoint,
)
from datp_core.domain.identifiers import CheckpointProfileId
from datp_core.domain.values import PositiveFloat, PositiveInt


def _convergence(
    *, rounds_initial: int = 40, window_rounds: int = 10, tolerance: float = 0.005
) -> CheckpointConvergenceRecord:
    return CheckpointConvergenceRecord(
        metric="federated_averaging_weighted_benign_validation_reconstruction_error",
        rounds_initial=PositiveInt(rounds_initial),
        rule="absolute_relative_change_between_the_first_and_last_losses_in_the_trailing_window_is_less_than_tolerance",
        formula="abs(loss_round_minus_9 - loss_round) / abs(loss_round_minus_9) < 0.005",
        zero_start_loss_behavior="relative_change_equals_zero",
        tolerance=PositiveFloat(tolerance),
        window_rounds=PositiveInt(window_rounds),
        window="trailing_ten_recorded_rounds",
        qualification="first_round_at_or_after_40_satisfying_the_rule",
        no_qualifying_round_behavior="select_the_150_round_cap",
    )


def test_first_qualifying_round_at_or_after_minimum_is_selected() -> None:
    # Losses follow 1/r until round 100, then plateau at 1/100. In the strictly decreasing
    # region the trailing 10-round relative change is 9/r (>= 0.09 within 150 rounds), so no
    # round qualifies until the whole window sits in the plateau: round 109 (window start 100).
    losses: list[tuple[int, float]] = []
    for r in range(1, 151):
        value = 1.0 / r if r <= 100 else 1.0 / 100
        losses.append((r, value))
    selected = select_anchor_checkpoint_round(convergence=_convergence(), recorded_losses=losses, round_cap=150)
    assert selected == 109


def test_no_qualifying_round_selects_the_cap() -> None:
    # Strictly halving every round keeps the window relative change well above tolerance.
    losses = [(r, 2.0**-r) for r in range(1, 151)]
    selected = select_anchor_checkpoint_round(convergence=_convergence(), recorded_losses=losses, round_cap=150)
    assert selected == 150


def test_before_minimum_round_never_qualifies() -> None:
    # Perfectly flat from the start: qualifies at the first round with a full window that is
    # also at or after the minimum round (40), never earlier.
    losses = [(r, 0.5) for r in range(1, 151)]
    selected = select_anchor_checkpoint_round(convergence=_convergence(), recorded_losses=losses, round_cap=150)
    assert selected == 40


def test_zero_window_start_loss_is_treated_as_converged() -> None:
    losses = [(r, 0.0) for r in range(1, 151)]
    selected = select_anchor_checkpoint_round(convergence=_convergence(), recorded_losses=losses, round_cap=150)
    assert selected == 40


def test_resolved_anchor_profile_exposes_the_convergence_contract() -> None:
    cfg = resolve_project_configuration()
    anchor = cfg.checkpoint_profiles.get(CheckpointProfileId("anchor_terminal_round"))
    assert anchor.convergence is not None
    assert anchor.convergence.rounds_initial == PositiveInt(40)
    assert anchor.convergence.window_rounds == PositiveInt(10)
    assert anchor.convergence.tolerance == PositiveFloat(0.005)
    assert anchor.selection.rule == "first_historically_qualifying_round_otherwise_150_round_cap"

    round_grid = cfg.checkpoint_profiles.get(CheckpointProfileId("datp_core_round_grid"))
    assert round_grid.convergence is None
    assert "auroc_driven_selection" in round_grid.selection.forbidden_selectors


def test_journal_selector_uses_scheduled_benign_losses_with_earliest_tie_break() -> None:
    selected = select_lowest_validation_loss_checkpoint(
        scheduled_rounds=(25, 50, 75), recorded_losses=((25, 0.2), (50, 0.1), (75, 0.1))
    )
    assert selected == 50


def test_cohort_selector_uses_mean_seed_loss_and_earliest_tie_break() -> None:
    selected = select_cohort_validation_checkpoint(
        scheduled_rounds=(25, 50, 75),
        seed_losses=(((25, 0.3), (50, 0.1), (75, 0.2)), ((25, 0.1), (50, 0.3), (75, 0.2))),
    )
    assert selected == 25
