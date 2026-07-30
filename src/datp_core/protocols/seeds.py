"""Seed declarations."""

from datp_core.domain.values import Seed

from .models import CONFIRMATORY_PAIRED_SEED_COUNT, SeedCohort

CONFIRMATORY_SEED_COHORT = SeedCohort(
    values=tuple(Seed(value) for value in range(CONFIRMATORY_PAIRED_SEED_COUNT.value))
)
