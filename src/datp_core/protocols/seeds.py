"""Seed declarations."""

from datp_core.domain.values import Seed

from .models import SeedCohort

CONFIRMATORY_SEED_COHORT = SeedCohort(values=tuple(Seed(value) for value in range(10)))
