"""Scientific contract: FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS selection ignores every test-derived signal."""

from dataclasses import dataclass

import pytest

from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values.ratios import MetricValue, ProximalCoefficient
from datp_core.protocols.training import (
    FEDPROX_COEFFICIENT_SELECTION_RULE,
    FEDPROX_COEFFICIENTS,
    require_non_test_fedprox_coefficient_selection_inputs,
    select_primary_fedprox_coefficient,
)


@dataclass(frozen=True, slots=True)
class _Candidate:
    coefficient: ProximalCoefficient
    mean_terminal_training_loss: MetricValue


def _candidates_with_lowest_loss_at(index: int) -> tuple[_Candidate, ...]:
    losses = [MetricValue(1.0), MetricValue(1.0), MetricValue(1.0), MetricValue(1.0)]
    losses[index] = MetricValue(0.01)
    return tuple(_Candidate(coefficient, loss) for coefficient, loss in zip(FEDPROX_COEFFICIENTS, losses, strict=True))


@pytest.mark.parametrize("index", range(4))
def test_selection_picks_the_coefficient_with_the_lowest_terminal_training_loss(index: int) -> None:
    candidates = _candidates_with_lowest_loss_at(index)
    selected = select_primary_fedprox_coefficient(candidates)
    assert selected.coefficient == FEDPROX_COEFFICIENTS[index]


def test_selection_breaks_exact_ties_with_the_smallest_coefficient() -> None:
    tied_loss = MetricValue(0.5)
    candidates = tuple(_Candidate(coefficient, tied_loss) for coefficient in FEDPROX_COEFFICIENTS)
    selected = select_primary_fedprox_coefficient(candidates)
    assert selected.coefficient == FEDPROX_COEFFICIENTS[0]


def test_selection_rejects_a_candidate_set_that_does_not_match_the_frozen_grid() -> None:
    candidates = (_Candidate(FEDPROX_COEFFICIENTS[0], MetricValue(0.5)),)
    with pytest.raises(ScientificContractError, match="frozen grid"):
        select_primary_fedprox_coefficient(candidates)


@pytest.mark.parametrize(
    "held_out_metrics",
    [
        (MetricValue(0.5),),
        (MetricValue(0.99), MetricValue(0.01)),
        (MetricValue(1.0),) * 5,
    ],
)
def test_guard_rejects_every_shape_of_held_out_metrics(held_out_metrics: tuple[MetricValue, ...]) -> None:
    with pytest.raises(LeakageError, match="held-out evaluation outcomes"):
        require_non_test_fedprox_coefficient_selection_inputs(
            selection_rule=FEDPROX_COEFFICIENT_SELECTION_RULE,
            held_out_metrics=held_out_metrics,
            attack_labels_present=False,
        )


def test_guard_rejects_attack_label_presence_regardless_of_other_arguments() -> None:
    with pytest.raises(LeakageError, match="attack labels"):
        require_non_test_fedprox_coefficient_selection_inputs(
            selection_rule=FEDPROX_COEFFICIENT_SELECTION_RULE,
            held_out_metrics=None,
            attack_labels_present=True,
        )


def test_guard_passes_with_only_training_time_information() -> None:
    require_non_test_fedprox_coefficient_selection_inputs(
        selection_rule=FEDPROX_COEFFICIENT_SELECTION_RULE,
        held_out_metrics=None,
        attack_labels_present=False,
    )
