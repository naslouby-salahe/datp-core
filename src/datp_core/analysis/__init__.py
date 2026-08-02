"""Statistical summaries, inference, mechanisms, and temporal analysis."""

from datp_core.analysis.descriptive import (
    DescriptiveSummary,
    NestedSeedSummary,
    QuantileRange,
    count_paired_differences,
    summarize_nested_replicates,
    summarize_values,
)
from datp_core.analysis.inference.bootstrap import (
    contrast_deltas,
    decide_confirmatory,
    external_paired_bca_interval,
    paired_bca_interval,
    validate_confirmatory_contrasts,
    validate_external_contrasts,
)
from datp_core.analysis.inference.paired import (
    holm_adjust,
    matched_pairs_rank_biserial,
    paired_wilcoxon,
)
from datp_core.analysis.mechanisms import (
    AssociationResult,
    ClusterPartitionSummary,
    ClusterStabilityResult,
    DivergenceBlocker,
    DivergenceResult,
    MechanismResult,
    ThresholdMovement,
    blocked_jensen_shannon_divergence,
    cluster_stability,
    decide_model_absorption,
    heterogeneity_benefit_association,
    threshold_movement,
)
from datp_core.analysis.models import (
    BcaAdjustment,
    BcaOutcome,
    BcaReason,
    BootstrapInterval,
    ExternalPairedAnalysisPlan,
    MetricSeries,
    MultiplicityDecision,
    MultiplicityResult,
    PairedContrast,
    PairedContrasts,
    PairedDifferenceCounts,
    PValue,
    RankBiserialResult,
    ScientificDecisionResult,
    WilcoxonAlternative,
    WilcoxonComputationMethod,
    WilcoxonResult,
    WilcoxonZeroMethod,
)
from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    TemporalFutureIdentity,
    TemporalInterpretation,
    TemporalRecoveryResult,
    decide_temporal,
    temporal_recovery,
    validate_frozen_recalibrated_pair,
)
