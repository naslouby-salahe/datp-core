"""Federated summary-statistic threshold estimators.

Each client contributes only aggregate summaries (count, mean, M2,
per-candidate exceedance counts). The server aggregates these summaries
without ever pooling raw client scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from datp_core.core.identifiers import ClientId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.enums import (
    ThresholdDiagnosticsKind,
    ThresholdPolicyKind,
    ThresholdScope,
    TieBreakRule,
)
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    FederatedFixedDiagnostics,
    FederatedMatchedDiagnostics,
    InsufficientCalibrationError,
    ThresholdingError,
    ThresholdRecord,
    ThresholdSet,
)

# ── Federated summary types ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientMomentSummary:
    """Per-client moment summary with stable M2 (Chan/Welford)."""

    client_id: ClientId
    count: int
    mean: float
    M2: float  # sum of squared deviations from the mean


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedMomentAggregate:
    """Pooled federated moment statistics."""

    total_count: int
    pooled_mean: float
    pooled_variance: float
    pooled_std: float


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientCandidateExceedanceSummary:
    """Per-client exceedance counts per candidate threshold."""

    client_id: ClientId
    calibration_count: int
    candidate_coefficients: tuple[float, ...]
    exceedance_counts: tuple[int, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateExceedanceAggregate:
    """Aggregated exceedance with achieved fractions."""

    total_calibration_count: int
    candidate_coefficients: tuple[float, ...]
    exceedance_counts: tuple[int, ...]
    achieved_fractions: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateSelectionResult:
    """Result of candidate-grid selection with full trace."""

    matched_coefficient: float
    achieved_exceedance: float
    deviation: float
    tie_set: tuple[float, ...]
    tie_rule: TieBreakRule


# ── Client-level moment computation ──────────────────────────────────────────


def compute_client_moments(
    calibration: tuple[BenignCalibrationScores, ...],
) -> tuple[ClientMomentSummary, ...]:
    """Compute per-client moment summaries using Welford's online algorithm.

    Uses the numerically stable Chan/Welford M2 formulation for squared
    deviations from the mean.
    """
    summaries: list[ClientMomentSummary] = []
    for item in calibration:
        values = item.values
        count = len(values)
        mean = values[0]
        m2 = 0.0
        for n in range(1, count):
            delta = values[n] - mean
            mean += delta / (n + 1)
            delta2 = values[n] - mean
            m2 += delta * delta2
        summaries.append(
            ClientMomentSummary(
                client_id=item.client_id,
                count=count,
                mean=mean,
                M2=m2,
            )
        )
    return tuple(summaries)


# ── Federated aggregation ────────────────────────────────────────────────────


def aggregate_moments(
    summaries: tuple[ClientMomentSummary, ...],
) -> FederatedMomentAggregate:
    """Aggregate client moment summaries into pooled federated statistics.

    Uses the standard federated decomposition with stable M2 within component:
        μ = Σ(n_k · μ_k) / Σ n_k
        σ² = Σ(M2_k) / Σ n_k  +  Σ(n_k · (μ_k − μ)²) / Σ n_k
            └── within ──┘     └──────── between ────────┘
    """
    total_count = sum(s.count for s in summaries)
    if total_count <= 0:
        raise InsufficientCalibrationError("Federated summary threshold has no calibration rows")
    pooled_mean = sum(s.count * s.mean for s in summaries) / total_count

    # Within-client variance component via stable M2
    within = sum(s.M2 for s in summaries) / total_count
    # Between-client variance component
    between = sum(s.count * (s.mean - pooled_mean) ** 2 for s in summaries) / total_count
    pooled_variance = within + between

    if pooled_variance < 0.0:
        raise ThresholdingError(f"Pooled variance is negative ({pooled_variance}); numerical instability detected")

    return FederatedMomentAggregate(
        total_count=total_count,
        pooled_mean=pooled_mean,
        pooled_variance=pooled_variance,
        pooled_std=math.sqrt(pooled_variance),
    )


# ── Candidate grid construction ──────────────────────────────────────────────


def build_candidate_grid(minimum: float, maximum: float, step: float) -> tuple[float, ...]:
    """Construct deterministic candidate grid using exact indexed arithmetic.

    Uses ``minimum + i * step`` for i = 0 .. num_steps.
    The config validator guarantees that ``(maximum - minimum) / step``
    is an integer within tolerance before this function is called.
    """
    num_steps = round((maximum - minimum) / step)
    candidates = tuple(minimum + i * step for i in range(num_steps + 1))
    if not math.isclose(candidates[0], minimum) or not math.isclose(candidates[-1], maximum):
        raise ThresholdingError(
            f"Candidate grid endpoints mismatch: first={candidates[0]}, last={candidates[-1]}, "
            f"expected min={minimum}, max={maximum}"
        )
    return candidates


# ── Exceedance computation ───────────────────────────────────────────────────


def compute_client_exceedance(
    client_id: ClientId,
    scores: tuple[float, ...],
    thresholds: tuple[float, ...],
    coefficients: tuple[float, ...],
) -> ClientCandidateExceedanceSummary:
    """Compute per-candidate exceedance counts for one client."""
    counts = [0] * len(thresholds)
    for score in scores:
        for i, threshold in enumerate(thresholds):
            if score > threshold:
                counts[i] += 1
    return ClientCandidateExceedanceSummary(
        client_id=client_id,
        calibration_count=len(scores),
        candidate_coefficients=coefficients,
        exceedance_counts=tuple(counts),
    )


def _validate_exceedance_summary(
    s: ClientCandidateExceedanceSummary,
    candidate_coefficients: tuple[float, ...],
    n_candidates: int,
    seen_ids: set[ClientId],
) -> int:
    """Validate one summary and return its calibration count."""
    if s.candidate_coefficients != candidate_coefficients:
        raise ThresholdingError(f"Client {s.client_id} has mismatched candidate coefficient grid")
    if len(s.exceedance_counts) != n_candidates:
        raise ThresholdingError(
            f"Client {s.client_id} exceedance counts length "
            f"({len(s.exceedance_counts)}) does not match expected "
            f"({n_candidates})"
        )
    if s.calibration_count <= 0:
        raise InsufficientCalibrationError(
            f"Client {s.client_id} has non-positive calibration count ({s.calibration_count})"
        )
    if s.client_id in seen_ids:
        raise ThresholdingError(f"Duplicate client ID: {s.client_id}")
    seen_ids.add(s.client_id)

    for count in s.exceedance_counts:
        if count < 0:
            raise ThresholdingError(f"Client {s.client_id} has negative exceedance count ({count})")
        if count > s.calibration_count:
            raise ThresholdingError(
                f"Client {s.client_id} exceedance count ({count}) exceeds calibration count ({s.calibration_count})"
            )

    return s.calibration_count


def aggregate_exceedance(
    summaries: tuple[ClientCandidateExceedanceSummary, ...],
) -> CandidateExceedanceAggregate:
    """Aggregate per-client exceedance summaries into achieved fractions."""
    if not summaries:
        raise InsufficientCalibrationError("No client exceedance summaries provided")

    n_candidates = len(summaries[0].exceedance_counts)
    candidate_coefficients = summaries[0].candidate_coefficients

    if len(candidate_coefficients) != n_candidates:
        raise ThresholdingError(
            f"Candidate coefficients count ({len(candidate_coefficients)}) "
            f"does not match exceedance counts length ({n_candidates})"
        )

    seen_ids: set[ClientId] = set()
    total_count = sum(
        _validate_exceedance_summary(s, candidate_coefficients, n_candidates, seen_ids) for s in summaries
    )

    if total_count <= 0:
        raise InsufficientCalibrationError("Total calibration count is zero")

    total_counts = [0] * n_candidates
    for s in summaries:
        for i, c in enumerate(s.exceedance_counts):
            total_counts[i] += c
    exceedance_counts = tuple(total_counts)
    achieved_fractions = tuple(c / total_count for c in exceedance_counts)

    for af in achieved_fractions:
        if not math.isfinite(af) or not (0.0 <= af <= 1.0):
            raise ThresholdingError(f"Achieved fraction {af} is not finite and in [0, 1]")

    return CandidateExceedanceAggregate(
        total_calibration_count=total_count,
        candidate_coefficients=candidate_coefficients,
        exceedance_counts=exceedance_counts,
        achieved_fractions=achieved_fractions,
    )


# ── Candidate selection ──────────────────────────────────────────────────────


def select_matched_candidate(
    aggregate: CandidateExceedanceAggregate,
    target: float,
) -> CandidateSelectionResult:
    """Select the candidate coefficient minimising |achieved - target|.

    When multiple candidates achieve the same deviation (tie), the highest
    coefficient is selected. The tie set and applied rule are recorded
    in the result.
    """
    achieved_fractions = aggregate.achieved_fractions
    candidates = aggregate.candidate_coefficients
    deviation = [abs(af - target) for af in achieved_fractions]
    min_deviation = min(deviation)
    tie_indices = [i for i, d in enumerate(deviation) if d == min_deviation]
    tie_set = tuple(candidates[i] for i in tie_indices)
    winner_idx = tie_indices[-1]
    winner = candidates[winner_idx]
    return CandidateSelectionResult(
        matched_coefficient=winner,
        achieved_exceedance=achieved_fractions[winner_idx],
        deviation=deviation[winner_idx],
        tie_set=tie_set,
        tie_rule=TieBreakRule.SELECT_HIGHEST_COEFFICIENT,
    )


# ── Top-level estimators ─────────────────────────────────────────────────────


def estimate_federated_matched(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    *,
    grid_minimum: float,
    grid_maximum: float,
    grid_step: float,
) -> ThresholdSet:
    """Matched-exceedance: select coefficient k* minimising |achieved - target|.

    Each client's exceedance count per candidate is aggregated server-side.
    Raw scores are never pooled into a single array.
    """
    if grid_step <= 0.0:
        raise ThresholdingError("Candidate grid step must be positive")
    if grid_minimum >= grid_maximum:
        raise ThresholdingError("Candidate grid minimum must be less than maximum")

    summaries = compute_client_moments(calibration)
    aggregate = aggregate_moments(summaries)
    if aggregate.pooled_std <= 0.0:
        raise ThresholdingError(
            "Federated pooled standard deviation is zero or negative; cannot construct candidate thresholds"
        )

    candidates = build_candidate_grid(grid_minimum, grid_maximum, grid_step)
    target = 1.0 - target_quantile.value
    thresholds = tuple(aggregate.pooled_mean + c * aggregate.pooled_std for c in candidates)

    # Aggregate per-client exceedance counts -- no raw-score pooling
    client_exceedances = []
    for item in calibration:
        client_exceedances.append(
            compute_client_exceedance(
                client_id=item.client_id,
                scores=item.values,
                thresholds=thresholds,
                coefficients=candidates,
            )
        )
    exceedance_aggregate = aggregate_exceedance(tuple(client_exceedances))

    result = select_matched_candidate(
        aggregate=exceedance_aggregate,
        target=target,
    )

    selected_threshold = aggregate.pooled_mean + result.matched_coefficient * aggregate.pooled_std
    diagnostics = FederatedMatchedDiagnostics(
        kind=ThresholdDiagnosticsKind.FEDERATED_MATCHED,
        matched_coefficient=result.matched_coefficient,
        target_exceedance=target,
        candidate_grid_minimum=grid_minimum,
        candidate_grid_maximum=grid_maximum,
        candidate_grid_step=grid_step,
        achieved_exceedance=tuple(
            zip(exceedance_aggregate.candidate_coefficients, exceedance_aggregate.achieved_fractions, strict=True)
        ),
        tie_set=result.tie_set,
        tie_rule=result.tie_rule,
        pooled_mean=aggregate.pooled_mean,
        pooled_standard_deviation=aggregate.pooled_std,
        selected_threshold=selected_threshold,
        selected_deviation=result.deviation,
        total_calibration_count=aggregate.total_count,
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.FEDERATED_MATCHED,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=selected_threshold,
                policy_kind=ThresholdPolicyKind.FEDERATED_MATCHED,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
        diagnostics=diagnostics,
    )


def estimate_federated_fixed(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    """Fixed-coefficient federated threshold: tau = mu + k * sigma."""
    summaries = compute_client_moments(calibration)
    aggregate = aggregate_moments(summaries)
    selected_threshold = aggregate.pooled_mean + coefficient * aggregate.pooled_std
    diagnostics = FederatedFixedDiagnostics(
        kind=ThresholdDiagnosticsKind.FEDERATED_FIXED,
        fixed_coefficient=coefficient,
        pooled_mean=aggregate.pooled_mean,
        pooled_standard_deviation=aggregate.pooled_std,
        selected_threshold=selected_threshold,
        total_calibration_count=aggregate.total_count,
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.FEDERATED_FIXED,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=selected_threshold,
                policy_kind=ThresholdPolicyKind.FEDERATED_FIXED,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
        diagnostics=diagnostics,
    )
