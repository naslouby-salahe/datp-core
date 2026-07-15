from enum import IntEnum, StrEnum

from datp_core.domain.errors import DomainValidationError


class ExperimentRole(StrEnum):
    CONFIRMATORY = "confirmatory"
    SUPPORTIVE = "supportive"
    EXTERNAL_VALIDATION = "external_validation"
    STRESS_TEST = "stress_test"
    MECHANISM = "mechanism"
    BOUNDARY = "boundary"
    EXPLORATORY = "exploratory"
    FUTURE_WORK = "future_work"
    FORBIDDEN = "forbidden"


class ClaimTier(IntEnum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4
    TIER_5 = 5
    TIER_6 = 6
    TIER_7 = 7
    TIER_8 = 8
    TIER_9 = 9


class ExecutionStatus(StrEnum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    SUPPRESSED = "suppressed"
    REJECTED = "rejected"
    FUTURE = "future"


def validate_role_tier(evidence_role: ExperimentRole, tier: ClaimTier) -> None:
    if (evidence_role is ExperimentRole.CONFIRMATORY) is (tier is ClaimTier.TIER_1):
        return

    raise DomainValidationError(
        detail="only confirmatory evidence may carry the Tier 1 claim",
        value=f"{evidence_role.value}:{tier.name}",
        constraint="confirmatory evidence role if and only if Tier 1",
    )
