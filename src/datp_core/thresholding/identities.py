"""Closed threshold-construction infeasibility identities and outcomes."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import require_contract
from datp_core.learning.federated.models import FederatedTrainingCoordinate


class ThresholdInfeasibilityReason(StrEnum):
    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = (
        "size_aware_shrinkage_function_unresolved"
    )
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = (
        "group_count_exceeds_eligible_population"
    )


@dataclass(frozen=True, slots=True)
class ThresholdUnavailableResult:
    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    reason: ThresholdInfeasibilityReason
    detail: str

    def __post_init__(self) -> None:
        require_contract(
            bool(self.detail.strip()),
            "an unavailable threshold result requires a human-readable detail",
            ContractSubject.THRESHOLD,
        )
