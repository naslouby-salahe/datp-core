from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import fsum, isfinite, sqrt

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.mathematics.dispersion import ClientMoment
from datp_core.domain.thresholding.policies import (
    FprTarget,
    ThresholdConstructionKind,
    ThresholdValue,
    validate_construction_kind,
)

_GRID_STEP = Decimal("0.01")
_GRID_MAXIMUM = Decimal("5.00")


class ThresholdComparatorRole(StrEnum):
    CENTRALIZED_MODEL_B0 = "centralized_model_b0"
    FED_STATS_BENIGN = "fed_stats_benign"


@dataclass(frozen=True, slots=True, kw_only=True)
class FedStatsK:
    value: Decimal

    def __post_init__(self) -> None:
        if type(self.value) is not Decimal or not self.value.is_finite() or self.value < Decimal(0):
            raise DomainValidationError(
                detail="FedStats k must be a finite non-negative Decimal",
                value=str(self.value),
                constraint="finite Decimal >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FedStatsPooledEvidence:
    global_mean: float
    global_variance: float
    within_term: float
    between_term: float
    between_ratio: float
    total_benign_count: int

    def __post_init__(self) -> None:
        if not _is_valid_pooled_evidence(self):
            raise DomainValidationError(
                detail="FedStats pooled evidence requires finite non-negative terms and a valid ratio",
                value=repr(self),
                constraint="positive count, finite terms, and 0 <= between ratio <= 1",
            )


def _is_valid_pooled_evidence(evidence: FedStatsPooledEvidence) -> bool:
    return all(
        (
            _is_positive_integer(evidence.total_benign_count),
            _has_finite_evidence_values(evidence),
            _has_non_negative_evidence_terms(evidence),
            _is_probability(evidence.between_ratio),
        )
    )


def _is_positive_integer(value: int) -> bool:
    return type(value) is int and value >= 1


def _has_finite_evidence_values(evidence: FedStatsPooledEvidence) -> bool:
    return all(
        isfinite(value)
        for value in (
            evidence.global_mean,
            evidence.global_variance,
            evidence.within_term,
            evidence.between_term,
            evidence.between_ratio,
        )
    )


def _has_non_negative_evidence_terms(evidence: FedStatsPooledEvidence) -> bool:
    return all(value >= 0 for value in (evidence.global_variance, evidence.within_term, evidence.between_term))


def _is_probability(value: float) -> bool:
    return 0 <= value <= 1


@dataclass(frozen=True, slots=True, kw_only=True)
class FedStatsCandidateExceedance:
    multiplier: FedStatsK
    benign_exceedance_count: int

    def __post_init__(self) -> None:
        if not _is_valid_candidate_exceedance(self):
            raise DomainValidationError(
                detail="FedStats candidate exceedance requires typed k and a non-negative integer count",
                value=repr(self),
                constraint="FedStatsK and integer count >= 0",
            )


def _is_valid_candidate_exceedance(candidate: FedStatsCandidateExceedance) -> bool:
    return type(candidate.multiplier) is FedStatsK and _is_non_negative_integer(candidate.benign_exceedance_count)


def _is_non_negative_integer(value: int) -> bool:
    return type(value) is int and value >= 0


@dataclass(frozen=True, slots=True, kw_only=True)
class FedStatsMatchedThreshold:
    multiplier: FedStatsK
    threshold: ThresholdValue
    benign_exceedance_count: int
    target_exceedance_rate: FprTarget


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class FedStatsBenignThresholdSpec:
    kind: ThresholdConstructionKind
    candidate_grid: tuple[FedStatsK, ...]
    fixed_k_supplementary: tuple[FedStatsK, ...]

    def __init__(self, *, kind: ThresholdConstructionKind) -> None:
        validate_construction_kind(value=kind, expected=ThresholdConstructionKind.FED_STATS_BENIGN)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "candidate_grid", _fixed_candidate_grid())
        object.__setattr__(
            self,
            "fixed_k_supplementary",
            (FedStatsK(value=Decimal("2.0")), FedStatsK(value=Decimal("2.5")), FedStatsK(value=Decimal("3.0"))),
        )

    def pooled_evidence(self, *, client_moments: tuple[ClientMoment, ...]) -> FedStatsPooledEvidence:
        if not _has_typed_client_moments(client_moments):
            raise DomainValidationError(
                detail="FedStats requires one typed benign client moment per reporting client",
                value=repr(client_moments),
                constraint="non-empty tuple of ClientMoment",
            )
        return _pooled_evidence_from_moments(client_moments)

    def select_matched_exceedance(
        self,
        *,
        pooled_evidence: FedStatsPooledEvidence,
        candidate_exceedances: tuple[FedStatsCandidateExceedance, ...],
        target_exceedance_rate: FprTarget,
    ) -> FedStatsMatchedThreshold:
        if not _is_valid_matched_exceedance_inputs(
            self, pooled_evidence, candidate_exceedances, target_exceedance_rate
        ):
            raise DomainValidationError(
                detail="FedStats matched-exceedance selection requires complete coherent typed evidence",
                value=repr(candidate_exceedances),
                constraint="typed pooled evidence, target, locked grid, and bounded counts",
            )
        selected = _closest_candidate(candidate_exceedances, pooled_evidence, target_exceedance_rate)
        return FedStatsMatchedThreshold(
            multiplier=selected.multiplier,
            threshold=ThresholdValue(
                value=pooled_evidence.global_mean
                + float(selected.multiplier.value) * sqrt(pooled_evidence.global_variance)
            ),
            benign_exceedance_count=selected.benign_exceedance_count,
            target_exceedance_rate=target_exceedance_rate,
        )


def _has_typed_client_moments(client_moments: tuple[ClientMoment, ...]) -> bool:
    return bool(client_moments) and all(type(moment) is ClientMoment for moment in client_moments)


def _pooled_evidence_from_moments(client_moments: tuple[ClientMoment, ...]) -> FedStatsPooledEvidence:
    total_count = sum(moment.sample_count for moment in client_moments)
    global_mean = fsum(moment.sample_count * moment.mean for moment in client_moments) / total_count
    within_term = fsum(moment.sample_count * moment.variance for moment in client_moments) / total_count
    between_term = (
        fsum(moment.sample_count * (moment.mean - global_mean) ** 2 for moment in client_moments) / total_count
    )
    global_variance = within_term + between_term
    return FedStatsPooledEvidence(
        global_mean=global_mean,
        global_variance=global_variance,
        within_term=within_term,
        between_term=between_term,
        between_ratio=_between_ratio(between_term, global_variance),
        total_benign_count=total_count,
    )


def _between_ratio(between_term: float, global_variance: float) -> float:
    if global_variance == 0:
        return 0.0
    return between_term / global_variance


def _is_valid_matched_exceedance_inputs(
    specification: FedStatsBenignThresholdSpec,
    pooled_evidence: FedStatsPooledEvidence,
    candidate_exceedances: tuple[FedStatsCandidateExceedance, ...],
    target_exceedance_rate: FprTarget,
) -> bool:
    return all(
        (
            type(pooled_evidence) is FedStatsPooledEvidence,
            type(target_exceedance_rate) is FprTarget,
            _has_locked_candidate_grid(specification, candidate_exceedances),
            _has_bounded_exceedance_counts(candidate_exceedances, pooled_evidence.total_benign_count),
        )
    )


def _has_locked_candidate_grid(
    specification: FedStatsBenignThresholdSpec,
    candidates: tuple[FedStatsCandidateExceedance, ...],
) -> bool:
    return (
        all(type(candidate) is FedStatsCandidateExceedance for candidate in candidates)
        and tuple(candidate.multiplier for candidate in candidates) == specification.candidate_grid
    )


def _has_bounded_exceedance_counts(
    candidates: tuple[FedStatsCandidateExceedance, ...], total_benign_count: int
) -> bool:
    return all(candidate.benign_exceedance_count <= total_benign_count for candidate in candidates)


def _closest_candidate(
    candidates: tuple[FedStatsCandidateExceedance, ...],
    pooled_evidence: FedStatsPooledEvidence,
    target_exceedance_rate: FprTarget,
) -> FedStatsCandidateExceedance:
    return min(
        candidates,
        key=lambda candidate: (
            abs(
                Decimal(candidate.benign_exceedance_count) / Decimal(pooled_evidence.total_benign_count)
                - target_exceedance_rate.value
            ),
            -candidate.multiplier.value,
        ),
    )


def _fixed_candidate_grid() -> tuple[FedStatsK, ...]:
    steps = int(_GRID_MAXIMUM / _GRID_STEP)
    return tuple(FedStatsK(value=index * _GRID_STEP) for index in range(steps + 1))
