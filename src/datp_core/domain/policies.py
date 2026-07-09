"""Threshold-policy, comparator, and training-algorithm identifiers.

Names are locked by docs/protocol/policies.md. No ``B5`` label exists (use
``B_FEDSTATS_BENIGN`` / ``B_LARIDI_FAITHFUL_DISCLOSURE``); no ``B3-LGS`` label
exists (use ``TAU_SHRINK`` — B3 stays family-mean and is never reused for
shrinkage).
"""

from __future__ import annotations

from enum import StrEnum


class ThresholdPolicy(StrEnum):
    """Core B0-B4 threshold-calibration-scope ladder."""

    B0 = "B0"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    B4 = "B4"


CORE_CAUSAL_LADDER: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy.B1,
    ThresholdPolicy.B2,
    ThresholdPolicy.B3,
    ThresholdPolicy.B4,
)
"""B0 is a centralized, privacy-incompatible reference; excluded from the FL causal ladder."""

B4_CANONICAL_K = 3
"""Pre-committed before results; other K values are exploratory only (SB-32)."""

B4_FINGERPRINT_FIELDS: tuple[str, ...] = ("mean", "std", "skewness", "p95")
"""Locked per-client fingerprint, standardized before k-means (Euclidean distance)."""


class Comparator(StrEnum):
    """Threshold variants, benign-only comparators, and stress-test comparators.

    None of these belong to :data:`CORE_CAUSAL_LADDER`.
    """

    TAU_SHRINK = "tau_shrink"
    CAL_SIZE_AWARE = "cal_size_aware"
    B2_CONF = "b2_conf"
    B_FEDSTATS_BENIGN = "b_fedstats_benign"
    B_LARIDI_FAITHFUL_DISCLOSURE = "b_laridi_faithful_disclosure"
    FEDPROX = "fedprox"
    DITTO = "ditto"
    FEDREP_AE = "fedrep_ae"
    FEDPER_AE = "fedper_ae"


STRESS_TEST_COMPARATORS: tuple[Comparator, ...] = (
    Comparator.FEDPROX,
    Comparator.DITTO,
    Comparator.FEDREP_AE,
    Comparator.FEDPER_AE,
)
"""Outside the causal threshold-scope ladder; never presented as sharing its control."""


class TrainingAlgorithm(StrEnum):
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"
    DITTO = "ditto"
    PERSONALIZED_FEDREP_AE = "personalized_fedrep_ae"
    PERSONALIZED_FEDPER_AE = "personalized_fedper_ae"


CORE_LADDER_TRAINING_ALGORITHM = TrainingAlgorithm.FEDAVG
"""FedAvg is the sole training baseline for the core B1-B4 causal ladder."""

PERSONALIZATION_FALLBACKS: tuple[TrainingAlgorithm, ...] = (
    TrainingAlgorithm.PERSONALIZED_FEDREP_AE,
    TrainingAlgorithm.PERSONALIZED_FEDPER_AE,
)
"""Used when the true Ditto algorithm is not faithfully implemented; a fallback run
must select one of these, never :attr:`TrainingAlgorithm.DITTO`."""
