"""Confirmatory inference declarations."""

from datp_core.domain.values import BootstrapReplicateCount, ClientCount, ConfidenceLevel

CONFIDENCE_LEVEL = ConfidenceLevel(0.95)
PAIRED_SEED_COUNT = ClientCount(10)
CONFIRMATORY_INTERVAL_METHOD = "bca_paired_arithmetic_mean"
SECONDARY_TEST = "wilcoxon_signed_rank"
SECONDARY_EFFECT_SIZE = "matched_pairs_rank_biserial"
SECONDARY_MULTIPLICITY = "holm"
BOOTSTRAP_REPLICATE_COUNT = BootstrapReplicateCount(10_000)
