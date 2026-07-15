from dataclasses import dataclass

from datp_core.application.ports.thresholding import ClusteringStrategy, QuantileEstimator, ThresholdStrategy
from datp_core.application.runtime.executor import PlanExecutor, StageRunner
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.scores import QuantileEstimatorType
from datp_core.domain.runtime.policies import PipelineStage
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry
from datp_core.domain.thresholding.policies import ThresholdConstructionKind
from datp_core.infrastructure.thresholding.clustering import ExactB4ClusteringStrategy
from datp_core.infrastructure.thresholding.federated_statistics import FedStatsThresholdStrategy
from datp_core.infrastructure.thresholding.policies import (
    ClusterAssignmentReader,
    ClusterThresholdStrategy,
    ExactThresholdConstructor,
    FamilyMembershipReader,
    FamilyThresholdStrategy,
    LocalThresholdStrategy,
    SharedThresholdStrategy,
)
from datp_core.infrastructure.thresholding.quantiles import CalibrationScoreReader, ExactQuantileEstimator
from datp_core.infrastructure.thresholding.variants import VariantThresholdStrategy


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdStrategyCollaborators:
    calibration_scores: CalibrationScoreReader
    family_memberships: FamilyMembershipReader
    cluster_assignments: ClusterAssignmentReader


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdStrategyRegistry:
    strategies: EnumMap[ThresholdConstructionKind, ThresholdStrategy]
    quantile_estimator: QuantileEstimator
    clustering_strategy: ClusteringStrategy
    constructor: ExactThresholdConstructor

    def __post_init__(self) -> None:
        _validate_threshold_registry(self.strategies)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageRunnerRegistry:
    runners: EnumMap[PipelineStage, StageRunner]

    def __post_init__(self) -> None:
        expected_stages = tuple(PipelineStage)
        entry_stages = tuple(entry.key for entry in self.runners.entries)
        if not all(
            (
                not self.runners.is_sparse,
                self.runners.allowed_keys == expected_stages,
                entry_stages == expected_stages,
            )
        ):
            raise DomainValidationError(
                detail="stage runner registry must bind every pipeline stage in declared order",
                value=repr(entry_stages),
                constraint="exhaustive ordered PipelineStage EnumMap",
            )

    def create_executor(self) -> PlanExecutor:
        return PlanExecutor(runners=self.runners)


def build_threshold_strategy_registry(
    collaborators: ThresholdStrategyCollaborators,
) -> ThresholdStrategyRegistry:
    shared = SharedThresholdStrategy(reader=collaborators.calibration_scores)
    local = LocalThresholdStrategy(reader=collaborators.calibration_scores)
    family = FamilyThresholdStrategy(
        reader=collaborators.calibration_scores,
        family_memberships=collaborators.family_memberships,
    )
    cluster = ClusterThresholdStrategy(
        reader=collaborators.calibration_scores,
        assignments=collaborators.cluster_assignments,
    )
    variants = VariantThresholdStrategy(
        reader=collaborators.calibration_scores,
        assignments=collaborators.cluster_assignments,
    )
    fed_stats = FedStatsThresholdStrategy(reader=collaborators.calibration_scores)
    strategies = EnumMap(
        entries=(
            EnumMapEntry(key=ThresholdConstructionKind.SHARED, value=shared),
            EnumMapEntry(key=ThresholdConstructionKind.LOCAL, value=local),
            EnumMapEntry(key=ThresholdConstructionKind.FAMILY, value=family),
            EnumMapEntry(key=ThresholdConstructionKind.CLUSTER, value=cluster),
            EnumMapEntry(key=ThresholdConstructionKind.ROBUST_CLUSTER_MEDIAN, value=variants),
            EnumMapEntry(key=ThresholdConstructionKind.SHRINKAGE, value=variants),
            EnumMapEntry(key=ThresholdConstructionKind.CALIB_SIZE_FALLBACK, value=variants),
            EnumMapEntry(key=ThresholdConstructionKind.CONFORMAL, value=variants),
            EnumMapEntry(key=ThresholdConstructionKind.FED_STATS_BENIGN, value=fed_stats),
        ),
        allowed_keys=tuple(ThresholdConstructionKind),
        is_sparse=False,
    )
    return ThresholdStrategyRegistry(
        strategies=strategies,
        quantile_estimator=ExactQuantileEstimator(
            estimator=QuantileEstimatorType.LOCAL_EXACT,
            reader=collaborators.calibration_scores,
        ),
        clustering_strategy=ExactB4ClusteringStrategy(reader=collaborators.calibration_scores),
        constructor=ExactThresholdConstructor(
            shared=shared,
            local=local,
            family=family,
            cluster=cluster,
            variants=variants,
            fed_stats=fed_stats,
        ),
    )


def _validate_threshold_registry(strategies: EnumMap[ThresholdConstructionKind, ThresholdStrategy]) -> None:
    expected_kinds = tuple(ThresholdConstructionKind)
    entry_kinds = tuple(entry.key for entry in strategies.entries)
    if not all(
        (
            not strategies.is_sparse,
            strategies.allowed_keys == expected_kinds,
            entry_kinds == expected_kinds,
        )
    ):
        raise DomainValidationError(
            detail="threshold strategy registry must bind every supported construction kind in declared order",
            value=repr(entry_kinds),
            constraint="exhaustive ordered ThresholdConstructionKind EnumMap",
        )
