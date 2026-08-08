"""Locked experiment seed cohorts."""

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import Seed, SeedCount

CONFIRMATORY_PAIRED_SEED_COUNT = SeedCount(10)


class SeedCohort(StrictModel):
    values: tuple[Seed, ...]

    @model_validator(mode="after")
    def validate_values(self) -> "SeedCohort":
        if not self.values:
            raise ValueError("a seed cohort requires at least one seed")
        if len(set(self.values)) != len(self.values):
            raise ValueError("seed cohort values must be unique")
        return self

    @property
    def member_count(self) -> SeedCount:
        return SeedCount(len(self.values))


CONFIRMATORY_SEED_COHORT = SeedCohort(
    values=tuple(Seed(value) for value in range(CONFIRMATORY_PAIRED_SEED_COUNT.value))
)
CONFIRMATORY_ANALYSIS_SEED = Seed(31)
ANCHOR_ANALYSIS_SEED = Seed(29)
BOUNDED_EVIDENCE_PAIRED_SEED_COUNT = SeedCount(10)
BOUNDED_EVIDENCE_SEED_COHORT = SeedCohort(
    values=tuple(Seed(value) for value in range(BOUNDED_EVIDENCE_PAIRED_SEED_COUNT.value))
)
