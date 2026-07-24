"""Dispatches typed analysis records to their owning capability implementation."""

from __future__ import annotations

from datp_core.analysis.calibration.coverage import analyze_conformal_coverage
from datp_core.analysis.calibration.quantile_estimation import analyze_quantile_estimation
from datp_core.analysis.calibration.threshold_stability import analyze_threshold_stability
from datp_core.analysis.clustering.stability import analyze_cluster_stability
from datp_core.analysis.comparisons.absorption import analyze_absorption
from datp_core.analysis.comparisons.association import analyze_association
from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.comparisons.paired import analyze_paired
from datp_core.analysis.comparisons.recovery_fraction import analyze_recovery_fraction
from datp_core.analysis.distributions.locked_client import analyze_locked_client_distribution
from datp_core.analysis.distributions.mechanism import analyze_distribution_mechanism
from datp_core.analysis.execution.plan import PairedAnalysisCell
from datp_core.analysis.operations.alert_burden import analyze_alert_burden
from datp_core.analysis.operations.resource_cost import analyze_resource_cost
from datp_core.analysis.result import AnalysisResult
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.analysis.temporal.recovery import analyze_temporal_recovery
from datp_core.analysis.validation.anchor_equivalence import analyze_anchor_equivalence
from datp_core.artifacts.models import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import RunId
from datp_core.core.values import Seed
from datp_core.experiments.models import (
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisKind,
    AnalysisRecord,
    AnchorEquivalenceAnalysisRecord,
    ClusterStabilityAnalysisRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    ExperimentRecord,
    LockedClientDistributionAnalysisRecord,
    MetricAssociationAnalysisRecord,
    PairedThresholdAnalysisRecord,
    QuantileEstimationAnalysisRecord,
    RecoveryFractionAnalysisRecord,
    ResourceCostAnalysisRecord,
    TemporalRecoveryAnalysisRecord,
    ThresholdStabilityAnalysisRecord,
)


def dispatch_paired(
    analysis: PairedThresholdAnalysisRecord,
    cells: tuple[PairedAnalysisCell, ...],
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> tuple[PairedThresholdAnalysisResult, ...]:
    return tuple(
        analyze_paired(
            analysis,
            config=config,
            repository=repository,
            statistical_analysis=statistical_analysis,
            experiment=experiment,
            seeds=seeds,
            run_id=run_id,
            partition_condition=cell.partition_condition,
            proximal_mu=cell.proximal_mu,
            ditto_weight=cell.ditto_weight,
            threshold_quantile=cell.threshold_quantile,
            shrinkage_weight=cell.shrinkage_weight,
            calibration_sample_count=cell.calibration_sample_count,
        )
        for cell in cells
    )


def dispatch(
    kind: AnalysisKind,
    analysis_record: AnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
    paired_results: tuple[PairedThresholdAnalysisResult, ...],
    calibration_sample_count_values: tuple[int | None, ...],
) -> list[AnalysisResult]:
    match kind:
        case AnalysisKind.METRIC_ASSOCIATION:
            assert isinstance(analysis_record, MetricAssociationAnalysisRecord)
            return [
                analyze_association(
                    analysis_record,
                    paired_results,
                    config=config,
                    repository=repository,
                    statistical_analysis=statistical_analysis,
                    experiment=experiment,
                    seeds=tuple(seed.value for seed in seeds),
                    run_id=run_id,
                )
            ]
        case AnalysisKind.THRESHOLD_STABILITY:
            assert isinstance(analysis_record, ThresholdStabilityAnalysisRecord)
            return [
                analyze_threshold_stability(
                    analysis_record,
                    config=config,
                    repository=repository,
                    experiment=experiment,
                    seeds=seeds,
                    run_id=run_id,
                    calibration_sample_count=calibration_sample_count,
                )
                for calibration_sample_count in calibration_sample_count_values
            ]
        case AnalysisKind.RECOVERY_FRACTION:
            assert isinstance(analysis_record, RecoveryFractionAnalysisRecord)
            return [analyze_recovery_fraction(analysis_record, paired_results)]
        case AnalysisKind.ABSORPTION:
            assert isinstance(analysis_record, AbsorptionAnalysisRecord)
            return [
                analyze_absorption(analysis_record, experiment, paired_results, config=config, repository=repository)
            ]
        case AnalysisKind.ANCHOR_EQUIVALENCE:
            assert isinstance(analysis_record, AnchorEquivalenceAnalysisRecord)
            return [analyze_anchor_equivalence(analysis_record, paired_results)]
        case AnalysisKind.TEMPORAL_RECOVERY:
            assert isinstance(analysis_record, TemporalRecoveryAnalysisRecord)
            return [
                analyze_temporal_recovery(
                    analysis_record,
                    config=config,
                    repository=repository,
                    statistical_analysis=statistical_analysis,
                    experiment=experiment,
                    seeds=seeds,
                    run_id=run_id,
                )
            ]
        case AnalysisKind.CLUSTER_STABILITY:
            assert isinstance(analysis_record, ClusterStabilityAnalysisRecord)
            return [
                analyze_cluster_stability(
                    analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                )
            ]
        case AnalysisKind.CONFORMAL_COVERAGE:
            assert isinstance(analysis_record, ConformalCoverageAnalysisRecord)
            return [
                analyze_conformal_coverage(
                    analysis_record,
                    config=config,
                    repository=repository,
                    experiment=experiment,
                    seeds=seeds,
                    run_id=run_id,
                )
            ]
        case AnalysisKind.DISTRIBUTION_MECHANISM:
            assert isinstance(analysis_record, DistributionMechanismAnalysisRecord)
            return [
                analyze_distribution_mechanism(
                    analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                )
            ]
        case AnalysisKind.LOCKED_CLIENT_DISTRIBUTION:
            assert isinstance(analysis_record, LockedClientDistributionAnalysisRecord)
            return [
                analyze_locked_client_distribution(
                    analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                )
            ]
        case AnalysisKind.ALERT_BURDEN:
            assert isinstance(analysis_record, AlertBurdenAnalysisRecord)
            return [analyze_alert_burden(analysis_record, config=config)]
        case AnalysisKind.QUANTILE_ESTIMATION:
            assert isinstance(analysis_record, QuantileEstimationAnalysisRecord)
            return [
                analyze_quantile_estimation(
                    analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                )
            ]
        case AnalysisKind.RESOURCE_COST:
            assert isinstance(analysis_record, ResourceCostAnalysisRecord)
            return [
                analyze_resource_cost(
                    analysis_record,
                    config=config,
                    repository=repository,
                    experiment=experiment,
                    seeds=seeds,
                    run_id=run_id,
                )
            ]
        case AnalysisKind.PAIRED_THRESHOLD:
            raise AssertionError("paired-threshold analyses are dispatched by dispatch_paired")


__all__ = ["dispatch", "dispatch_paired"]
