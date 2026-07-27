"""Seed cohort contract — pure resolved seed cohort records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import SeedCohortId
from datp_core.core.numbers import PositiveInt
from datp_core.core.seeding import Seed


class SeedCohortRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: SeedCohortId
    paired_seed_count: PositiveInt
    training_seeds: tuple[Seed, ...]
    bootstrap_analysis_seed: Seed
    analysis_seed_model: str
