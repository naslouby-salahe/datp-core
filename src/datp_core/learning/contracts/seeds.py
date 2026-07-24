"""Seed cohort contract — pure resolved seed cohort records."""

from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import SeedCohortId
from datp_core.core.numbers import PositiveInt
from datp_core.core.seeding import Seed


@define(frozen=True, slots=True, kw_only=True)
class SeedCohortRecord:
    identifier: SeedCohortId
    paired_seed_count: PositiveInt
    training_seeds: tuple[Seed, ...]
    bootstrap_analysis_seed: Seed
    analysis_seed_model: str
