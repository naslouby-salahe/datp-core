"""Regime identifiers, roles, and pass rules (docs/protocol/regimes.md)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.metrics import Metric


class Regime(StrEnum):
    A = "A"
    B_A = "B_A"
    B_B_REJECTED_NO_METADATA = "B_B_REJECTED_NO_METADATA"
    C = "C"
    D = "D"
    D_TEMPORAL = "D_TEMPORAL"


class RegimeRole(StrEnum):
    """A role is not interchangeable: only CONFIRMATORY carries the confirmatory claim."""

    CONFIRMATORY = "confirmatory"
    BOUNDARY = "boundary"
    REJECTED = "rejected"
    SUPPORTIVE = "supportive"
    EXTERNAL_VALIDATION = "external_validation"


@dataclass(frozen=True)
class RegimeSpec:
    regime: Regime
    role: RegimeRole
    primary_metric: Metric
    pass_rule: str


REGIME_SPECS: dict[Regime, RegimeSpec] = {
    Regime.A: RegimeSpec(
        regime=Regime.A,
        role=RegimeRole.CONFIRMATORY,
        primary_metric=Metric.CV_FPR,
        pass_rule=(
            "10-seed BCa CI on CV(FPR)[B1]-CV(FPR)[B2] excludes zero, positive direction; "
            "revise honestly otherwise, never suppressed"
        ),
    ),
    Regime.B_A: RegimeSpec(
        regime=Regime.B_A,
        role=RegimeRole.BOUNDARY,
        primary_metric=Metric.CV_FPR,
        pass_rule=(
            "a null result is reported strictly as an applicability boundary; "
            "never generalized to CICIoT2023 as a whole; carries no confirmatory-style metric row"
        ),
    ),
    Regime.B_B_REJECTED_NO_METADATA: RegimeSpec(
        regime=Regime.B_B_REJECTED_NO_METADATA,
        role=RegimeRole.REJECTED,
        primary_metric=Metric.CV_FPR,
        pass_rule="no metadata columns available; suppression note only, never a metric row",
    ),
    Regime.C: RegimeSpec(
        regime=Regime.C,
        role=RegimeRole.SUPPORTIVE,
        primary_metric=Metric.CV_FPR,
        pass_rule=(
            "report gain vs alpha; overlapping low-alpha seed ranges reported as a "
            "high-heterogeneity band, not strict monotonicity"
        ),
    ),
    Regime.D: RegimeSpec(
        regime=Regime.D,
        role=RegimeRole.EXTERNAL_VALIDATION,
        primary_metric=Metric.CV_FPR,
        pass_rule="eligibility-coverage gate: proceed only if n_k >= 100 for >= 90% of clients",
    ),
    Regime.D_TEMPORAL: RegimeSpec(
        regime=Regime.D_TEMPORAL,
        role=RegimeRole.BOUNDARY,
        primary_metric=Metric.CV_FPR,
        pass_rule="exactly one of three pre-specified recovery outcomes applies; no retroactive streaming detector",
    ),
}

CONFIRMATORY_REGIMES: tuple[Regime, ...] = tuple(
    regime for regime, spec in REGIME_SPECS.items() if spec.role is RegimeRole.CONFIRMATORY
)
