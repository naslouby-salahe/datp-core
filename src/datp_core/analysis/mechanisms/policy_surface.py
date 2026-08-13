from enum import StrEnum

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import CalibrationSize, MetricValue, Seed


class PolicySurfaceState(StrEnum):
    UNIQUE_SHARED_THRESHOLD = "UNIQUE_SHARED_THRESHOLD"
    UNIQUE_LOCAL_THRESHOLD = "UNIQUE_LOCAL_THRESHOLD"
    UNIQUE_CLUSTER_THRESHOLD = "UNIQUE_CLUSTER_THRESHOLD"
    UNIQUE_LOCAL_GLOBAL_SHRINKAGE = "UNIQUE_LOCAL_GLOBAL_SHRINKAGE"
    UNIQUE_SIZE_AWARE_SHRINKAGE = "UNIQUE_SIZE_AWARE_SHRINKAGE"
    MULTIPLE_NONDOMINATED = "MULTIPLE_NONDOMINATED"
    UNAVAILABLE_NO_VALID_CV = "UNAVAILABLE_NO_VALID_CV"
    UNAVAILABLE_NO_COMMON_ATTACK_UTILITY = "UNAVAILABLE_NO_COMMON_ATTACK_UTILITY"


_SUPPORTED_POLICIES = frozenset(
    {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
        FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
    }
)


class PolicySurfacePolicyMetric(StrictModel):
    policy: FederatedThresholdMethod
    cv_fpr: MetricValue | None
    p10_macro_f1: MetricValue | None
    worst_client_balanced_accuracy: MetricValue | None

    @model_validator(mode="after")
    def validate_policy(self) -> "PolicySurfacePolicyMetric":
        if self.policy not in _SUPPORTED_POLICIES:
            raise ValueError("policy surface admits only the interaction-grid policies")
        return self


class PolicySurfaceCell(StrictModel):
    seed: Seed
    alpha_label: str
    calibration_size: CalibrationSize | None
    heterogeneity: MetricValue
    policies: tuple[PolicySurfacePolicyMetric, ...]
    nondominated_policies: tuple[FederatedThresholdMethod, ...]
    state: PolicySurfaceState

    @model_validator(mode="after")
    def validate_surface_state(self) -> "PolicySurfaceCell":
        policies = tuple(item.policy for item in self.policies)
        if not policies or len(policies) != len(frozenset(policies)):
            raise ValueError("policy surface cells require unique policies")
        if tuple(sorted(self.nondominated_policies, key=lambda policy: policy.value)) != self.nondominated_policies:
            raise ValueError("nondominated policies must be ordered")
        if self.state is PolicySurfaceState.UNAVAILABLE_NO_VALID_CV:
            if any(item.cv_fpr is not None for item in self.policies) or self.nondominated_policies:
                raise ValueError("no-valid-CV state cannot include a nondominated set")
        elif self.state is PolicySurfaceState.UNAVAILABLE_NO_COMMON_ATTACK_UTILITY:
            if any(item.p10_macro_f1 is not None for item in self.policies) or self.nondominated_policies:
                raise ValueError("no-common-attack-utility state cannot include a nondominated set")
        elif len(self.nondominated_policies) == 1:
            expected = PolicySurfaceState(f"UNIQUE_{self.nondominated_policies[0].name}")
            if self.state is not expected:
                raise ValueError("unique nondominated policy must use its exact typed state")
        elif len(self.nondominated_policies) > 1:
            if self.state is not PolicySurfaceState.MULTIPLE_NONDOMINATED:
                raise ValueError("multiple nondominated policies require the multiple state")
        else:
            raise ValueError("available surface cells require one or more nondominated policies")
        return self


def policy_surface_cell(
    *,
    seed: Seed,
    alpha_label: str,
    calibration_size: CalibrationSize | None,
    heterogeneity: MetricValue,
    policies: tuple[PolicySurfacePolicyMetric, ...],
) -> PolicySurfaceCell:
    """Classify one predeclared cell without fitting or selecting a policy."""

    if not policies:
        raise ValueError("policy surface requires one or more policy metrics")
    if not any(item.cv_fpr is not None for item in policies):
        return PolicySurfaceCell(
            seed=seed,
            alpha_label=alpha_label,
            calibration_size=calibration_size,
            heterogeneity=heterogeneity,
            policies=policies,
            nondominated_policies=(),
            state=PolicySurfaceState.UNAVAILABLE_NO_VALID_CV,
        )
    if any(item.cv_fpr is None for item in policies) or any(item.p10_macro_f1 is None for item in policies):
        return PolicySurfaceCell(
            seed=seed,
            alpha_label=alpha_label,
            calibration_size=calibration_size,
            heterogeneity=heterogeneity,
            policies=policies,
            nondominated_policies=(),
            state=PolicySurfaceState.UNAVAILABLE_NO_COMMON_ATTACK_UTILITY,
        )
    nondominated = tuple(
        sorted(
            (
                candidate.policy
                for candidate in policies
                if not any(_dominates(other, candidate) for other in policies if other.policy is not candidate.policy)
            ),
            key=lambda policy: policy.value,
        )
    )
    state = (
        PolicySurfaceState(f"UNIQUE_{nondominated[0].name}")
        if len(nondominated) == 1
        else PolicySurfaceState.MULTIPLE_NONDOMINATED
    )
    return PolicySurfaceCell(
        seed=seed,
        alpha_label=alpha_label,
        calibration_size=calibration_size,
        heterogeneity=heterogeneity,
        policies=policies,
        nondominated_policies=nondominated,
        state=state,
    )


def _dominates(left: PolicySurfacePolicyMetric, right: PolicySurfacePolicyMetric) -> bool:
    if left.cv_fpr is None or right.cv_fpr is None or left.p10_macro_f1 is None or right.p10_macro_f1 is None:
        return False
    return (
        left.cv_fpr.value <= right.cv_fpr.value
        and left.p10_macro_f1.value >= right.p10_macro_f1.value
        and (left.cv_fpr.value < right.cv_fpr.value or left.p10_macro_f1.value > right.p10_macro_f1.value)
    )
