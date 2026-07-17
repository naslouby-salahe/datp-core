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
from datp_core.domain.data.partitioning import (
    ClientPartitionSpec,
    DeviceClientPartitionSpec,
    DirichletPartitionSpec,
    FilePseudoClientPartitionSpec,
    GroupClientPartitionSpec,
    NaturalDevicePartitionSpec,
)
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
from datp_core.domain.experiments.identities import DetectorBranchId, EvaluationArmId
from datp_core.domain.learning.checkpoints import CheckpointSchedule, CheckpointSelectionSpec, RecoveryCheckpointPolicy
from datp_core.domain.learning.scores import ScoreGenerationSpec
from datp_core.domain.learning.training import AggregationStrategy, ModelPersonalizationStrategy, TrainingSpec
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


class DetectorBranchRole(StrEnum):
    CORE_FEDAVG = "core_fedavg"
    FEDPROX_STRESS_TEST = "fedprox_stress_test"
    PERSONALIZATION_STRESS_TEST = "personalization_stress_test"


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
class RegimeDataSpec:
    dataset: DatasetSpec
    partitioning: ClientPartitionSpec
    splits: SplitCollectionSpec
    preprocessing: PreprocessingSpec

    def __post_init__(self) -> None:
        if not _has_regime_data_component_types(self):
            raise DomainValidationError(
                detail="regime data requires every dataset/partition/split/preprocessing specification typed",
                value=repr(self),
                constraint="Architecture section 5.4 regime-data ownership",
            )
        if not _has_regime_data_split_types(self.splits):
            raise DomainValidationError(
                detail="regime data requires exactly one training, benign-calibration, and test split",
                value=repr(self.splits),
                constraint="TrainingSplitSpec, BenignCalibrationSplitSpec, TestSplitSpec",
            )


_PARTITION_SPECIFICATION_TYPES = (
    NaturalDevicePartitionSpec,
    FilePseudoClientPartitionSpec,
    DeviceClientPartitionSpec,
    GroupClientPartitionSpec,
    DirichletPartitionSpec,
)


def _has_regime_data_component_types(regime_data: RegimeDataSpec) -> bool:
    return all(
        (
            type(regime_data.dataset) is DatasetSpec,
            type(regime_data.partitioning) in _PARTITION_SPECIFICATION_TYPES,
            type(regime_data.splits) is SplitCollectionSpec,
            type(regime_data.preprocessing) is PreprocessingSpec,
        )
    )


def _has_regime_data_split_types(splits: SplitCollectionSpec) -> bool:
    return all(
        (
            type(splits.training) is TrainingSplitSpec,
            type(splits.calibration) is BenignCalibrationSplitSpec,
            type(splits.test) is TestSplitSpec,
        )
    )


def _detector_branch_role_for(training: TrainingSpec) -> DetectorBranchRole:
    if training.personalization is not ModelPersonalizationStrategy.NONE:
        return DetectorBranchRole.PERSONALIZATION_STRESS_TEST
    match training.federation.aggregation:
        case AggregationStrategy.FEDAVG:
            return DetectorBranchRole.CORE_FEDAVG
        case AggregationStrategy.FEDPROX:
            return DetectorBranchRole.FEDPROX_STRESS_TEST
        case _:
            assert_never(training.federation.aggregation)


@dataclass(frozen=True, slots=True, kw_only=True)
class DetectorBranchSpec:
    branch_id: DetectorBranchId
    role: DetectorBranchRole
    training: TrainingSpec
    checkpointing: CheckpointSchedule
    checkpoint_selection: CheckpointSelectionSpec
    scoring: ScoreGenerationSpec

    def __post_init__(self) -> None:
        if not _has_detector_branch_component_types(self):
            raise DomainValidationError(
                detail="detector branch requires typed training, checkpoint, and scoring specifications",
                value=repr(self),
                constraint="Architecture section 5.5 detector-branch ownership",
            )
        expected_role = _detector_branch_role_for(self.training)
        if self.role is not expected_role:
            raise DomainValidationError(
                detail="detector branch role must match the aggregation/personalization it actually trains",
                value=repr(self.role),
                constraint=repr(expected_role),
            )


def _has_detector_branch_component_types(branch: DetectorBranchSpec) -> bool:
    return all(
        (
            type(branch.branch_id) is DetectorBranchId,
            type(branch.role) is DetectorBranchRole,
            type(branch.training) is TrainingSpec,
            type(branch.checkpointing) is CheckpointSchedule,
            type(branch.checkpoint_selection) is CheckpointSelectionSpec,
            type(branch.scoring) is ScoreGenerationSpec,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationArmSpec:
    arm_id: EvaluationArmId
    detector_branch_id: DetectorBranchId
    thresholds: ThresholdSuiteSpec
    evaluation: EvaluationSuiteSpec
    resource_costs: ResourceCostSuiteSpec | None

    def __post_init__(self) -> None:
        if not _has_evaluation_arm_component_types(self):
            raise DomainValidationError(
                detail="evaluation arm requires a typed detector-branch reference, thresholds, and evaluation suite",
                value=repr(self),
                constraint="Architecture section 5.6 evaluation-arm ownership",
            )


def _has_evaluation_arm_component_types(arm: EvaluationArmSpec) -> bool:
    return (
        type(arm.arm_id) is EvaluationArmId
        and type(arm.detector_branch_id) is DetectorBranchId
        and type(arm.thresholds) is ThresholdSuiteSpec
        and type(arm.evaluation) in {StandardEvaluationSuiteSpec, AlertBurdenEvaluationSuiteSpec}
        and (arm.resource_costs is None or type(arm.resource_costs) is ResourceCostSuiteSpec)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificProtocolSpec:
    track: ProtocolTrack
    regime_data: RegimeDataSpec
    detector_branch: DetectorBranchSpec
    evaluation_arm: EvaluationArmSpec
    statistics: StatisticalAnalysisSpec

    def __post_init__(self) -> None:
        if not _has_protocol_component_types(self):
            raise DomainValidationError(
                detail="scientific protocol requires every scientific specification in its declared typed position",
                value=repr(self),
                constraint="Architecture section 8.1 scientific aggregate",
            )
        if self.evaluation_arm.detector_branch_id != self.detector_branch.branch_id:
            raise DomainValidationError(
                detail="an evaluation arm must reference the detector branch it was resolved alongside",
                value=repr(self.evaluation_arm.detector_branch_id),
                constraint=repr(self.detector_branch.branch_id),
            )

    def identity_inputs(self) -> tuple[ScientificIdentityInput, ...]:
        return tuple(
            ScientificIdentityInput(
                field=field,
                earliest_stage=self.earliest_identity_stage_for(field),
                value=self.value_for(field),
            )
            for field in ScientificProtocolField
        )

    def value_for(self, field: ScientificProtocolField) -> object:
        match field:
            case ScientificProtocolField.TRACK:
                return self.track
            case ScientificProtocolField.DATASET:
                return self.regime_data.dataset
            case ScientificProtocolField.PARTITIONING:
                return self.regime_data.partitioning
            case ScientificProtocolField.SPLITS:
                return self.regime_data.splits
            case ScientificProtocolField.PREPROCESSING:
                return self.regime_data.preprocessing
            case ScientificProtocolField.TRAINING:
                return self.detector_branch.training
            case ScientificProtocolField.CHECKPOINTING:
                return self.detector_branch.checkpointing
            case ScientificProtocolField.CHECKPOINT_SELECTION:
                return self.detector_branch.checkpoint_selection
            case ScientificProtocolField.SCORING:
                return self.detector_branch.scoring
            case ScientificProtocolField.THRESHOLDS:
                return self.evaluation_arm.thresholds
            case ScientificProtocolField.EVALUATION:
                return self.evaluation_arm.evaluation
            case ScientificProtocolField.STATISTICS:
                return self.statistics
            case ScientificProtocolField.RESOURCE_COSTS:
                return self.evaluation_arm.resource_costs
            case _:
                assert_never(field)

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
    return (
        type(protocol.track) is ProtocolTrack
        and type(protocol.regime_data) is RegimeDataSpec
        and type(protocol.detector_branch) is DetectorBranchSpec
        and type(protocol.evaluation_arm) is EvaluationArmSpec
        and type(protocol.statistics) is StatisticalAnalysisSpec
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
