from dataclasses import dataclass
from typing import assert_never

from datp_core.domain.evaluation.statistical_results import ClaimOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimWording:
    outcome: ClaimOutcome
    template: str


def select_claim_wording(outcome: ClaimOutcome) -> ClaimWording:
    match outcome:
        case ClaimOutcome.STRONG_POSITIVE:
            template = (
                "B2 reduces CV(FPR) from [B1] to [B2] (10-seed BCa CI [a, b], excluding zero); "
                "all seed deltas positive."
            )
        case ClaimOutcome.WEAK_POSITIVE:
            template = (
                "B2 reduces CV(FPR) with a 10-seed BCa CI [a, b] that excludes zero but is wide; "
                "the effect is directionally consistent though the magnitude is uncertain at this seed count."
            )
        case ClaimOutcome.MIXED:
            template = (
                "The reduction is present in most seeds; the BCa CI [a, b] excludes zero, but seed [x] "
                "shows attenuation attributable to [cause], reported as a stability caveat."
            )
        case ClaimOutcome.NULL:
            template = (
                "At 10 seeds the BCa CI [a, b] includes zero; the confirmatory endpoint is not met at this power. "
                "We report the point estimate and the failure to exclude zero rather than the 5-seed result."
            )
        case ClaimOutcome.OPPOSITE:
            template = (
                "B2 increases CV(FPR) relative to B1 in this regime (CI [a, b], positive lower bound in the "
                "opposite direction), which we report as an unexpected reversal and analyze in §Mechanism."
            )
        case ClaimOutcome.FEASIBILITY_REJECTION:
            template = "The required feasibility condition was not met; the claim is not made."
        case ClaimOutcome.SUPPRESSED:
            template = "The output is suppressed under the pre-specified rule."
        case _:
            assert_never(outcome)
    return ClaimWording(outcome=outcome, template=template)
