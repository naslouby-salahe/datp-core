import pytest

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.claims import (
    ClaimTier,
    ExecutionStatus,
    ExperimentRole,
    validate_role_tier,
)


def test_claim_vocabulary_is_closed_and_ordered() -> None:
    assert tuple(ExperimentRole) == (
        ExperimentRole.CONFIRMATORY,
        ExperimentRole.SUPPORTIVE,
        ExperimentRole.EXTERNAL_VALIDATION,
        ExperimentRole.STRESS_TEST,
        ExperimentRole.MECHANISM,
        ExperimentRole.BOUNDARY,
        ExperimentRole.EXPLORATORY,
        ExperimentRole.FUTURE_WORK,
        ExperimentRole.FORBIDDEN,
    )
    assert tuple(ClaimTier) == tuple(ClaimTier(value) for value in range(1, 10))
    assert tuple(ExecutionStatus) == (
        ExecutionStatus.MANDATORY,
        ExecutionStatus.OPTIONAL,
        ExecutionStatus.SUPPRESSED,
        ExecutionStatus.REJECTED,
        ExecutionStatus.FUTURE,
    )


def test_confirmatory_evidence_requires_tier_one() -> None:
    validate_role_tier(ExperimentRole.CONFIRMATORY, ClaimTier.TIER_1)

    with pytest.raises(DomainValidationError):
        validate_role_tier(ExperimentRole.CONFIRMATORY, ClaimTier.TIER_2)


@pytest.mark.parametrize("role", tuple(role for role in ExperimentRole if role is not ExperimentRole.CONFIRMATORY))
def test_non_confirmatory_evidence_rejects_tier_one(role: ExperimentRole) -> None:
    with pytest.raises(DomainValidationError):
        validate_role_tier(role, ClaimTier.TIER_1)
