"""Federated exceedance aggregation from typed summaries — no raw scores."""

from __future__ import annotations

import math

import pytest

from datp_core.core.identifiers import ClientId
from datp_core.thresholding.enums import TieBreakRule
from datp_core.thresholding.estimators.federated import (
    CandidateExceedanceAggregate,
    ClientCandidateExceedanceSummary,
    aggregate_exceedance,
    select_matched_candidate,
)
from datp_core.thresholding.models import (
    InsufficientCalibrationError,
    ThresholdingError,
)

_COEFFICIENTS = (0.0, 1.0, 2.0)
_CLIENT_A = ClientId("a")
_CLIENT_B = ClientId("b")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _summary(
    client_id: ClientId,
    calibration_count: int,
    exceedance_counts: tuple[int, ...],
    coefficients: tuple[float, ...] = _COEFFICIENTS,
) -> ClientCandidateExceedanceSummary:
    return ClientCandidateExceedanceSummary(
        client_id=client_id,
        calibration_count=calibration_count,
        candidate_coefficients=coefficients,
        exceedance_counts=exceedance_counts,
    )


# ── aggregate_exceedance validation ─────────────────────────────────────────


class TestAggregateExceedanceValidation:
    def test_empty_summaries_rejected(self) -> None:
        with pytest.raises(InsufficientCalibrationError, match="No client exceedance summaries"):
            aggregate_exceedance(())

    def test_mismatched_coefficients_rejected(self) -> None:
        summaries = (
            _summary(_CLIENT_A, 10, (5, 3, 1)),
            _summary(_CLIENT_B, 10, (5, 3, 1), coefficients=(9.9,)),
        )
        with pytest.raises(ThresholdingError, match="mismatched candidate coefficient"):
            aggregate_exceedance(summaries)

    def test_negative_exceedance_rejected(self) -> None:
        summaries = (
            _summary(_CLIENT_A, 10, (5, -1, 3)),
        )
        with pytest.raises(ThresholdingError, match="negative exceedance"):
            aggregate_exceedance(summaries)

    def test_exceedance_exceeds_calibration_rejected(self) -> None:
        summaries = (
            _summary(_CLIENT_A, 10, (11, 3, 1)),
        )
        with pytest.raises(ThresholdingError, match="exceeds"):
            aggregate_exceedance(summaries)

    def test_duplicate_client_id_rejected(self) -> None:
        summaries = (
            _summary(_CLIENT_A, 10, (5, 3, 1)),
            _summary(_CLIENT_A, 10, (4, 2, 0)),
        )
        with pytest.raises(ThresholdingError, match="Duplicate client"):
            aggregate_exceedance(summaries)

    def test_non_positive_calibration_count_rejected(self) -> None:
        summaries = (
            _summary(_CLIENT_A, 0, (0, 0, 0)),
        )
        with pytest.raises(InsufficientCalibrationError, match="non-positive calibration"):
            aggregate_exceedance(summaries)

    def test_zero_total_calibration_rejected(self) -> None:
        summaries = (
            _summary(_CLIENT_A, 0, (0, 0, 0)),
            _summary(_CLIENT_B, 0, (0, 0, 0)),
        )
        with pytest.raises(InsufficientCalibrationError, match="non-positive"):
            aggregate_exceedance(summaries)


# ── aggregate_exceedance computation ─────────────────────────────────────────


class TestAggregateExceedanceComputation:
    def test_single_client(self) -> None:
        result = aggregate_exceedance(
            (_summary(_CLIENT_A, 5, (4, 2, 0)),)
        )
        assert result.total_calibration_count == 5
        assert result.candidate_coefficients == _COEFFICIENTS
        assert result.exceedance_counts == (4, 2, 0)
        assert result.achieved_fractions == (0.8, 0.4, 0.0)

    def test_multi_client_aggregation(self) -> None:
        result = aggregate_exceedance(
            (
                _summary(_CLIENT_A, 10, (8, 5, 2)),
                _summary(_CLIENT_B, 15, (12, 8, 3)),
            )
        )
        assert result.total_calibration_count == 25
        assert result.candidate_coefficients == _COEFFICIENTS
        # (8+12, 5+8, 2+3)
        assert result.exceedance_counts == (20, 13, 5)
        expected = (20 / 25, 13 / 25, 5 / 25)
        for got, exp in zip(result.achieved_fractions, expected, strict=True):
            assert math.isclose(got, exp)

    def test_achieved_fractions_in_unit_interval(self) -> None:
        result = aggregate_exceedance(
            (
                _summary(_CLIENT_A, 10, (10, 5, 0)),
                _summary(_CLIENT_B, 10, (10, 5, 0)),
            )
        )
        for af in result.achieved_fractions:
            assert 0.0 <= af <= 1.0
            assert math.isfinite(af)


# ── select_matched_candidate from aggregate (no raw scores) ──────────────────


class TestSelectMatchedCandidate:
    def test_accepts_aggregate_without_raw_scores(self) -> None:
        """select_matched_candidate works from CandidateExceedanceAggregate only."""
        aggregate = CandidateExceedanceAggregate(
            total_calibration_count=20,
            candidate_coefficients=_COEFFICIENTS,
            exceedance_counts=(15, 10, 5),
            achieved_fractions=(0.75, 0.5, 0.25),
        )
        result = select_matched_candidate(aggregate, target=0.5)
        assert result.matched_coefficient == 1.0
        assert math.isclose(result.achieved_exceedance, 0.5)
        assert math.isclose(result.deviation, 0.0)

    def test_tie_break_selects_highest_coefficient(self) -> None:
        """Multiple candidates with same deviation — highest coefficient wins."""
        aggregate = CandidateExceedanceAggregate(
            total_calibration_count=20,
            candidate_coefficients=_COEFFICIENTS,
            exceedance_counts=(10, 10, 10),
            achieved_fractions=(0.5, 0.5, 0.5),
        )
        result = select_matched_candidate(aggregate, target=0.5)
        assert result.matched_coefficient == 2.0
        assert result.tie_set == _COEFFICIENTS
        assert result.tie_rule == TieBreakRule.SELECT_HIGHEST_COEFFICIENT

    def test_no_tie_picks_closest(self) -> None:
        aggregate = CandidateExceedanceAggregate(
            total_calibration_count=8,
            candidate_coefficients=_COEFFICIENTS,
            exceedance_counts=(6, 3, 1),
            achieved_fractions=(0.75, 0.375, 0.125),
        )
        result = select_matched_candidate(aggregate, target=0.5)
        assert result.matched_coefficient == 1.0
        assert math.isclose(result.deviation, 0.125)


# ── End-to-end server-side: summaries → aggregate → select (no scores) ──────


class TestServerSideAggregation:
    """Prove server-side pipeline works without raw BenignCalibrationScores."""

    def test_aggregate_then_select(self) -> None:
        """Construct summaries manually, aggregate, select — no scores involved."""
        summaries = (
            ClientCandidateExceedanceSummary(
                client_id=_CLIENT_A,
                calibration_count=10,
                candidate_coefficients=_COEFFICIENTS,
                exceedance_counts=(8, 5, 2),
            ),
            ClientCandidateExceedanceSummary(
                client_id=_CLIENT_B,
                calibration_count=15,
                candidate_coefficients=_COEFFICIENTS,
                exceedance_counts=(12, 8, 3),
            ),
        )
        aggregate = aggregate_exceedance(summaries)
        result = select_matched_candidate(aggregate, target=0.5)

        assert aggregate.total_calibration_count == 25
        assert aggregate.candidate_coefficients == _COEFFICIENTS
        assert aggregate.exceedance_counts == (20, 13, 5)
        assert math.isclose(aggregate.achieved_fractions[1], 13 / 25)
        assert result.matched_coefficient == 1.0
        assert result.tie_rule == TieBreakRule.SELECT_HIGHEST_COEFFICIENT
