"""Seed declarations."""

from datp_core.domain.values import ClientCount

from .models import SeedCohort

CONFIRMATORY_PAIRED_SEED_COUNT = ClientCount(10)
CONFIRMATORY_SEED_COHORT = SeedCohort(values=tuple(range(10)))
