"""Closed threshold-construction infeasibility identities."""

from enum import StrEnum


class ThresholdInfeasibilityReason(StrEnum):
    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = (
        "size_aware_shrinkage_function_unresolved"
    )
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = (
        "group_count_exceeds_eligible_population"
    )
