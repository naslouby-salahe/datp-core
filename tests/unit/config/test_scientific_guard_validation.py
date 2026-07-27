"""Configuration-time guards for locked scientific contracts."""

import pytest
from pydantic import ValidationError

from datp_core.config.authored.protocols import SeedCohortConfig


def test_seed_cohort_rejects_duplicate_or_count_mismatched_seeds() -> None:
    with pytest.raises(ValidationError, match="unique"):
        SeedCohortConfig(
            paired_seed_count=2, training_seeds=[1, 1], bootstrap_analysis_seed=300, analysis_seed_model="fixed"
        )
    with pytest.raises(ValidationError, match="paired_seed_count"):
        SeedCohortConfig(
            paired_seed_count=2, training_seeds=[1], bootstrap_analysis_seed=300, analysis_seed_model="fixed"
        )
