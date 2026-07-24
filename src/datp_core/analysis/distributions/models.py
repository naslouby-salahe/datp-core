"""Result records for distribution-mechanism and locked-client distribution analyses."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define

from datp_core.evaluation.distributions import ClientScoreDistributionRecord, ThresholdTradeoffEntry


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismSeedResult:
    seed: int
    evaluations: Mapping[str, Mapping[str, ClientScoreDistributionRecord]]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismRawResult:
    analysis_label: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffSeedResult:
    seed: int
    per_client_tradeoff: Mapping[str, ThresholdTradeoffEntry]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffResult:
    analysis_label: str
    field_formulas: Mapping[str, str]
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismTradeoffSeedResult, ...]


DistributionMechanismAnalysisResult = DistributionMechanismRawResult | DistributionMechanismTradeoffResult


@define(frozen=True, slots=True, kw_only=True)
class LockedClientDistributionAnalysisResult:
    analysis_label: str
    locked_client_identifier: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


__all__ = [
    "DistributionMechanismAnalysisResult",
    "DistributionMechanismRawResult",
    "DistributionMechanismSeedResult",
    "DistributionMechanismTradeoffResult",
    "DistributionMechanismTradeoffSeedResult",
    "LockedClientDistributionAnalysisResult",
]
