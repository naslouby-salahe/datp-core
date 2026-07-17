from dataclasses import dataclass, fields
from enum import StrEnum
from typing import assert_never

from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    ArtifactRetentionPolicy,
    SerializationFormat,
    WriteDisposition,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.data.datasets import DatasetSpec
from datp_core.domain.data.partitioning import ClientPartitionSpec
from datp_core.domain.data.preprocessing import PreprocessingSpec
from datp_core.domain.data.splitting import (
    BenignCalibrationSplitSpec,
    SplitCollectionSpec,
    TestSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import CostDerivationKind
from datp_core.domain.evaluation.metrics import ResourceMetric
from datp_core.domain.evaluation.operating_points import (
    AlertBurdenEvaluationSuiteSpec,
    EvaluationSuiteSpec,
    StandardEvaluationSuiteSpec,
)
from datp_core.domain.evaluation.statistical_results import ClaimOutcome, StatisticalAnalysisSpec
from datp_core.domain.learning.checkpoints import CheckpointSchedule, CheckpointSelectionSpec, RecoveryCheckpointPolicy
from datp_core.domain.learning.scores import ScoreGenerationSpec
from datp_core.domain.learning.training import TrainingSpec
from datp_core.domain.runtime.policies import (
    DeviceSpec,
    ExecutionMode,
    ParallelismSpec,
    PipelineStage,
    ResourceBudget,
    ResourcePressurePolicy,
)
from datp_core.domain.runtime.seeds import EnumMap, SeedRoleTuple
from datp_core.domain.thresholding.policies import ThresholdSuiteSpec


class ProtocolTrack(StrEnum):
    DATP_ANCHOR = "datp_anchor"
    COMPLETE = "complete"


class ReportArtifactType(StrEnum):
    MAIN_TABLE = "main_table"
    SUPPLEMENT_TABLE = "supplement_table"
    FIGURE = "figure"
    WORDING_BLOCK = "wording_block"


class TableType(StrEnum):
    CONFIRMATORY_INTERVAL = "confirmatory_interval"
    DISPERSION_LADDER = "dispersion_ladder"
    SENSITIVITY_GRID = "sensitivity_grid"
    COMPARATOR = "comparator"
    STRESS_TEST = "stress_test"
    CLUSTER_STABILITY = "cluster_stability"
    CONTINGENCY = "contingency"
    BOUNDARY_NULL = "boundary_null"
    ALERT_BURDEN = "alert_burden"
    COMMUNICATION_STORAGE_COST = "communication_storage_cost"


class FigureType(StrEnum):
    CDF_OVERLAY = "cdf_overlay"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    LAMBDA_CURVE = "lambda_curve"
    RECOVERY_CURVE = "recovery_curve"
    SEVERITY_TREND = "severity_trend"


class ScientificProtocolField(StrEnum):
    TRACK = "track"
    DATASET = "dataset"
    PARTITIONING = "partitioning"
    SPLITS = "splits"
    PREPROCESSING = "preprocessing"
    TRAINING = "training"
    CHECKPOINTING = "checkpointing"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    SCORING = "scoring"
    THRESHOLDS = "thresholds"
    EVALUATION = "evaluation"
    STATISTICS = "statistics"
    RESOURCE_COSTS = "resource_costs"


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceCostSuiteSpec:
    metrics: tuple[ResourceMetric, ...]
    derivation: CostDerivationKind
    evidence_rule: str

    def __post_init__(self) -> None:
        if not _is_valid_resource_cost_suite(self):
            raise DomainValidationError(
                detail="resource-cost suite requires unique requested metrics and an explicit evidence rule",
                value=repr(self),
                constraint="non-empty unique ResourceMetric tuple, CostDerivationKind, non-empty evidence rule",
            )


def _is_valid_resource_cost_suite(specification: ResourceCostSuiteSpec) -> bool:
    return all(
        (
            _has_unique_resource_metrics(specification.metrics),
            type(specification.derivation) is CostDerivationKind,
            type(specification.evidence_rule) is str,
            bool(specification.evidence_rule),
        )
    )


def _has_unique_resource_metrics(metrics: tuple[ResourceMetric, ...]) -> bool:
    return (
        bool(metrics)
        and all(type(metric) is ResourceMetric for metric in metrics)
        and len(set(metrics)) == len(metrics)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificIdentityInput:
    field: ScientificProtocolField
    earliest_stage: PipelineStage
    value: object


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificProtocolSpec:
    track: ProtocolTrack
    dataset: DatasetSpec
    partitioning: ClientPartitionSpec
    splits: SplitCollectionSpec
    preprocessing: PreprocessingSpec
    training: TrainingSpec
    checkpointing: CheckpointSchedule
    checkpoint_selection: CheckpointSelectionSpec
    scoring: ScoreGenerationSpec
    thresholds: ThresholdSuiteSpec
    evaluation: EvaluationSuiteSpec
    statistics: StatisticalAnalysisSpec
    resource_costs: ResourceCostSuiteSpec | None

    def __post_init__(self) -> None:
        if not _has_protocol_component_types(self):
            raise DomainValidationError(
                detail="scientific protocol requires every scientific specification in its declared typed position",
                value=repr(self),
                constraint="Architecture section 8.1 scientific aggregate",
            )
        if not _has_protocol_split_types(self.splits):
            raise DomainValidationError(
                detail="scientific protocol requires exactly one training, benign-calibration, and test split",
                value=repr(self.splits),
                constraint="TrainingSplitSpec, BenignCalibrationSplitSpec, TestSplitSpec",
            )

    def identity_inputs(self) -> tuple[ScientificIdentityInput, ...]:
        return tuple(
            ScientificIdentityInput(
                field=field,
                earliest_stage=self.earliest_identity_stage_for(field),
                value=getattr(self, field.value),
            )
            for field in ScientificProtocolField
        )

    @staticmethod
    def earliest_identity_stage_for(field: ScientificProtocolField) -> PipelineStage:
        match field:
            case ScientificProtocolField.TRACK | ScientificProtocolField.DATASET:
                return PipelineStage.SOURCE_INSPECTION
            case ScientificProtocolField.PARTITIONING:
                return PipelineStage.PARTITION
            case ScientificProtocolField.SPLITS:
                return PipelineStage.SPLIT_BUILD
            case ScientificProtocolField.PREPROCESSING:
                return PipelineStage.PREPROCESSOR_FIT
            case ScientificProtocolField.TRAINING:
                return PipelineStage.TRAIN
            case ScientificProtocolField.CHECKPOINTING | ScientificProtocolField.CHECKPOINT_SELECTION:
                return PipelineStage.CHECKPOINT_SELECT
            case ScientificProtocolField.SCORING:
                return PipelineStage.CALIBRATION_SCORE
            case ScientificProtocolField.THRESHOLDS:
                return PipelineStage.THRESHOLD
            case ScientificProtocolField.EVALUATION:
                return PipelineStage.EVALUATE
            case ScientificProtocolField.STATISTICS:
                return PipelineStage.ANALYZE
            case ScientificProtocolField.RESOURCE_COSTS:
                return PipelineStage.RESOURCE_COST
            case _:
                assert_never(field)


def _has_protocol_component_types(protocol: ScientificProtocolSpec) -> bool:
    return all(
        (
            _has_protocol_core_types(protocol),
            _has_protocol_training_types(protocol),
            _has_protocol_evaluation_types(protocol),
        )
    )


def _has_protocol_core_types(protocol: ScientificProtocolSpec) -> bool:
    return all(
        (
            type(protocol.track) is ProtocolTrack,
            type(protocol.dataset) is DatasetSpec,
            type(protocol.partitioning) is not ClientPartitionSpec,
            type(protocol.splits) is SplitCollectionSpec,
            type(protocol.preprocessing) is PreprocessingSpec,
        )
    )


def _has_protocol_training_types(protocol: ScientificProtocolSpec) -> bool:
    return all(
        (
            type(protocol.training) is TrainingSpec,
            type(protocol.checkpointing) is CheckpointSchedule,
            type(protocol.checkpoint_selection) is CheckpointSelectionSpec,
            type(protocol.scoring) is ScoreGenerationSpec,
            type(protocol.thresholds) is ThresholdSuiteSpec,
        )
    )


def _has_protocol_evaluation_types(protocol: ScientificProtocolSpec) -> bool:
    return (
        type(protocol.evaluation) in {StandardEvaluationSuiteSpec, AlertBurdenEvaluationSuiteSpec}
        and type(protocol.statistics) is StatisticalAnalysisSpec
        and (protocol.resource_costs is None or type(protocol.resource_costs) is ResourceCostSuiteSpec)
    )


def _has_protocol_split_types(splits: SplitCollectionSpec) -> bool:
    return all(
        (
            type(splits.training) is TrainingSplitSpec,
            type(splits.calibration) is BenignCalibrationSplitSpec,
            type(splits.test) is TestSplitSpec,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionPolicy:
    execution_mode: ExecutionMode
    device: DeviceSpec
    budget: ResourceBudget
    parallelism: ParallelismSpec
    seed_roles: SeedRoleTuple
    resource_pressure: ResourcePressurePolicy
    recovery: RecoveryCheckpointPolicy

    def __post_init__(self) -> None:
        if not _has_execution_policy_component_types(self):
            raise DomainValidationError(
                detail="execution policy accepts only declared operational policy specifications",
                value=repr(self),
                constraint="Architecture section 8.2 ExecutionPolicy fields",
            )


def _has_execution_policy_component_types(policy: ExecutionPolicy) -> bool:
    return all(
        (
            type(policy.execution_mode) is ExecutionMode,
            type(policy.device) is DeviceSpec,
            type(policy.budget) is ResourceBudget,
            type(policy.parallelism) is ParallelismSpec,
            type(policy.seed_roles) is SeedRoleTuple,
            type(policy.resource_pressure) is ResourcePressurePolicy,
            type(policy.recovery) is RecoveryCheckpointPolicy,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactPolicy:
    namespace: ArtifactNamespace
    write_disposition: WriteDisposition
    serialization_defaults: EnumMap[ArtifactType, SerializationFormat]
    retention: ArtifactRetentionPolicy

    def __post_init__(self) -> None:
        if not _has_artifact_policy_component_types(self):
            raise DomainValidationError(
                detail="artifact policy requires typed namespace, write, serialization, and retention policies",
                value=repr(self),
                constraint="Architecture section 8.2 ArtifactPolicy fields",
            )


def _has_artifact_policy_component_types(policy: ArtifactPolicy) -> bool:
    return all(
        (
            type(policy.namespace) is ArtifactNamespace,
            type(policy.write_disposition) is WriteDisposition,
            type(policy.serialization_defaults) is EnumMap,
            type(policy.retention) is ArtifactRetentionPolicy,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportingPolicy:
    tables: tuple[TableType, ...]
    figures: tuple[FigureType, ...]
    report_artifacts: tuple[ReportArtifactType, ...]
    formats: EnumMap[ReportArtifactType, tuple[SerializationFormat, ...]]
    wording_outcomes: tuple[ClaimOutcome, ...]

    def __post_init__(self) -> None:
        if not _is_valid_reporting_policy(self):
            raise DomainValidationError(
                detail="reporting policy requires unique typed render targets and formats for every requested artifact",
                value=repr(self),
                constraint="typed unique report fields and complete format mapping",
            )


def _is_valid_reporting_policy(policy: ReportingPolicy) -> bool:
    return all(
        (
            _has_unique_typed_values(policy.tables, TableType),
            _has_unique_typed_values(policy.figures, FigureType),
            _has_unique_typed_values(policy.report_artifacts, ReportArtifactType),
            _has_unique_typed_values(policy.wording_outcomes, ClaimOutcome),
            _has_reporting_format_contract(policy),
        )
    )


def _has_unique_typed_values[T: StrEnum](values: tuple[T, ...], expected_type: type[T]) -> bool:
    return all(type(value) is expected_type for value in values) and len(set(values)) == len(values)


def _has_reporting_format_contract(policy: ReportingPolicy) -> bool:
    formats = policy.formats
    return (
        type(formats) is EnumMap
        and tuple(entry.key for entry in formats.entries) == policy.report_artifacts
        and all(entry.value for entry in formats.entries)
    )


def policy_field_names() -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(field.name for field in fields(policy)) for policy in (ExecutionPolicy, ArtifactPolicy, ReportingPolicy)
    )
