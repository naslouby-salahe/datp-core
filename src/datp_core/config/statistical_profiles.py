"""Statistical-profile configuration schema: how a statistical procedure (BCa/percentile
bootstrap, Wilcoxon, etc.) and the nested-replicate aggregation policy are authored.

This is scientific *configuration* schema, not an analysis-execution feature, so it lives under
``datp_core.config`` rather than ``datp_core.analysis`` -- keeping it under ``analysis`` previously
made every data/learning/thresholding/evaluation handler that transitively imports
``ResolvedProjectConfiguration`` also transitively import the analysis package, violating this
repository's own layering contract (`importlinter.ini`'s
``data-thresholding-evaluation-do-not-import-downstream-features``). Kept as its own leaf module
(rather than merged into `config.models`) so both `config.models` and `config.resolution.protocols`
can depend on it without a circular import between them; `analysis.statistics.inference` (the one
analysis-side consumer) imports it from here, which is an ordinary analysis-depends-on-config
direction and does not reintroduce the violation.
"""

from __future__ import annotations

from enum import StrEnum

from attrs import define

from datp_core.core.identifiers import StatisticalProfileId
from datp_core.core.numbers import PositiveInt, Probability


class BootstrapMethod(StrEnum):
    BCA_BOOTSTRAP = "bca_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"


class StatisticalMethod(StrEnum):
    """Every `statistical_profiles.*.method` value authored in protocols.yaml.

    A superset of `BootstrapMethod`: comparisons like `profile.method in {BootstrapMethod.X, ...}`
    remain valid because `StrEnum` members compare equal across classes by string value.
    """

    BCA_BOOTSTRAP = "bca_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"
    RATIO_OF_SEED_LEVEL_MEANS = "ratio_of_seed_level_means"
    DESCRIPTIVE_SUMMARY = "descriptive_summary"
    SPEARMAN_CORRELATION = "spearman_correlation"
    LINEAR_REGRESSION = "linear_regression"


@define(frozen=True, slots=True, kw_only=True)
class StatisticalProfileRecord:
    """Resolved, executable statistical analysis contract (BCa/percentile bootstrap, Wilcoxon, etc.)."""

    identifier: StatisticalProfileId
    method: StatisticalMethod | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


@define(frozen=True, slots=True, kw_only=True)
class NestedReplicatePolicyRecord:
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


__all__ = [
    "BootstrapMethod",
    "NestedReplicatePolicyRecord",
    "StatisticalMethod",
    "StatisticalProfileRecord",
]
