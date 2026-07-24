"""Authored experiment catalogue schema, composed from its focused submodules."""

from __future__ import annotations

from datp_core.config.authored.experiments.analyses import (
    AbsorptionAnalysisConfig,
    AlertBurdenAnalysisConfig,
    AnalysisSpecConfig,
    AnchorEquivalenceAnalysisConfig,
    ClusterStabilityAnalysisConfig,
    ConformalCoverageAnalysisConfig,
    DistributionMechanismAnalysisConfig,
    LockedClientDistributionAnalysisConfig,
    MetricAssociationAnalysisConfig,
    PairedThresholdAnalysisConfig,
    QuantileEstimationAnalysisConfig,
    RecoveryFractionAnalysisConfig,
    ResourceCostAnalysisConfig,
    TemporalRecoveryAnalysisConfig,
    ThresholdStabilityAnalysisConfig,
)
from datp_core.config.authored.experiments.catalogue import (
    AuthoredExperimentConfig,
    AuthoredExperimentsCatalogueConfig,
    AuthoredStudyPopulationConfig,
    CapabilityRequirementConfig,
    EligibilityGateConfig,
    PrerequisiteSpecConfig,
)
from datp_core.config.authored.experiments.evaluations import EvaluationSpecConfig
from datp_core.config.authored.experiments.sweeps import (
    CalibrationSubsetConfig,
    SweepConditionConfig,
    SweepVariableConfig,
)

__all__ = [
    "AbsorptionAnalysisConfig",
    "AlertBurdenAnalysisConfig",
    "AnalysisSpecConfig",
    "AnchorEquivalenceAnalysisConfig",
    "AuthoredExperimentConfig",
    "AuthoredExperimentsCatalogueConfig",
    "AuthoredStudyPopulationConfig",
    "CalibrationSubsetConfig",
    "CapabilityRequirementConfig",
    "ClusterStabilityAnalysisConfig",
    "ConformalCoverageAnalysisConfig",
    "DistributionMechanismAnalysisConfig",
    "EligibilityGateConfig",
    "EvaluationSpecConfig",
    "LockedClientDistributionAnalysisConfig",
    "MetricAssociationAnalysisConfig",
    "PairedThresholdAnalysisConfig",
    "PrerequisiteSpecConfig",
    "QuantileEstimationAnalysisConfig",
    "RecoveryFractionAnalysisConfig",
    "ResourceCostAnalysisConfig",
    "SweepConditionConfig",
    "SweepVariableConfig",
    "TemporalRecoveryAnalysisConfig",
    "ThresholdStabilityAnalysisConfig",
]
