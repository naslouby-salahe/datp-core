"""Resolution of authored threshold policy configs into domain threshold policy records."""

from __future__ import annotations

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.authored.protocols.thresholds import (
    CalibrationFallbackPolicyConfig,
    CentralizedPooledThresholdPolicyConfig,
    ClusterThresholdPolicyConfig,
    FamilyMeanThresholdPolicyConfig,
    FederatedFixedCoefficientPolicyConfig,
    FederatedMatchedExceedancePolicyConfig,
    LocalGlobalShrinkagePolicyConfig,
    LocalQuantileThresholdPolicyConfig,
    SharedMeanThresholdPolicyConfig,
    SharedPooledThresholdPolicyConfig,
    SharedWeightedThresholdPolicyConfig,
    SplitConformalThresholdPolicyConfig,
    TypedThresholdPolicyConfig,
)
from datp_core.config.errors import ConfigurationError
from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.thresholding.enums import ClusterAggregation, FingerprintFeature, ThresholdPolicyKind
from datp_core.thresholding.policies import (
    ClusterPolicy,
    ConformalPolicy,
    FederatedPolicy,
    QuantilePolicy,
    ShrinkagePolicy,
    ThresholdPolicyRecord,
)


def resolve_threshold_policy(cfg: TypedThresholdPolicyConfig) -> ThresholdPolicyRecord:
    """Convert an authored threshold-policy variant into its domain record."""
    if isinstance(cfg, SharedMeanThresholdPolicyConfig):
        return QuantilePolicy(kind=ThresholdPolicyKind.SHARED_MEAN, quantile=cfg.quantile)
    if isinstance(cfg, SharedPooledThresholdPolicyConfig):
        return QuantilePolicy(kind=ThresholdPolicyKind.SHARED_POOLED, quantile=cfg.quantile)
    if isinstance(cfg, SharedWeightedThresholdPolicyConfig):
        return QuantilePolicy(kind=ThresholdPolicyKind.SHARED_WEIGHTED, quantile=cfg.quantile)
    if isinstance(cfg, LocalQuantileThresholdPolicyConfig):
        return QuantilePolicy(kind=ThresholdPolicyKind.LOCAL_QUANTILE, quantile=cfg.quantile)
    if isinstance(cfg, FamilyMeanThresholdPolicyConfig):
        return QuantilePolicy(kind=ThresholdPolicyKind.FAMILY_MEAN, quantile=cfg.quantile)
    if isinstance(cfg, CentralizedPooledThresholdPolicyConfig):
        return QuantilePolicy(kind=ThresholdPolicyKind.SHARED_POOLED, quantile=cfg.quantile)
    if isinstance(cfg, ClusterThresholdPolicyConfig):
        return ClusterPolicy(
            kind=ThresholdPolicyKind.CLUSTER,
            quantile=cfg.quantile,
            cluster_count=cfg.cluster_count,
            aggregation=ClusterAggregation(cfg.aggregation),
            fingerprint_features=tuple(FingerprintFeature(f) for f in cfg.fingerprint_features),
            kmeans_random_seed=int(cfg.clustering["random_seed"]),
            kmeans_initialization_runs=int(cfg.clustering["initialization_runs"]),
            kmeans_maximum_iterations=int(cfg.clustering["maximum_iterations"]),
            kmeans_convergence_tolerance=float(cfg.clustering["convergence_tolerance"]),
        )
    if isinstance(cfg, SplitConformalThresholdPolicyConfig):
        return ConformalPolicy(
            kind=ThresholdPolicyKind.CONFORMAL,
            coverage_alpha=cfg.coverage_alpha,
            minimum_sample_count=cfg.minimum_sample_count,
        )
    if isinstance(cfg, LocalGlobalShrinkagePolicyConfig):
        return ShrinkagePolicy(
            kind=ThresholdPolicyKind.SHRINKAGE,
            quantile=cfg.quantile,
            shrinkage_weight=cfg.shrinkage_weight,
        )
    if isinstance(cfg, CalibrationFallbackPolicyConfig):
        return ShrinkagePolicy(
            kind=ThresholdPolicyKind.CALIBRATION_FALLBACK,
            quantile=cfg.quantile,
            n_half=cfg.weight_formula_constants["n_half"],
        )
    if isinstance(cfg, FederatedMatchedExceedancePolicyConfig):
        return FederatedPolicy(
            kind=ThresholdPolicyKind.FEDERATED_MATCHED,
            quantile=cfg.quantile,
            primary_comparator=cfg.primary_comparator,
            candidate_grid_minimum=float(cfg.candidate_grid["minimum"]),
            candidate_grid_maximum=float(cfg.candidate_grid["maximum"]),
            candidate_grid_step=float(cfg.candidate_grid["step"]),
        )
    if isinstance(cfg, FederatedFixedCoefficientPolicyConfig):
        return FederatedPolicy(
            kind=ThresholdPolicyKind.FEDERATED_FIXED,
            quantile=cfg.quantile,
            primary_comparator=cfg.primary_comparator,
            fixed_k=cfg.fixed_k if cfg.fixed_k is not None else None,
        )
    raise ConfigurationError(f"Unsupported authored threshold policy configuration: {type(cfg).__name__}")


def resolve_threshold_policies(authored: AuthoredProtocolsConfig) -> dict[ThresholdPolicyId, ThresholdPolicyRecord]:
    return {
        ThresholdPolicyId(tp_key): resolve_threshold_policy(tp_cfg)
        for tp_key, tp_cfg in authored.threshold_policies.items()
    }
