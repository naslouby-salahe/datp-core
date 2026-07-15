from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError


class IntegrityStatus(StrEnum):
    INTACT = "intact"
    CORRUPT = "corrupt"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


class SchemaCompatibility(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class ReuseDecisionKind(StrEnum):
    REUSE = "reuse"
    RECOMPUTE = "recompute"
    BLOCKED = "blocked"


class ReuseImpact(StrEnum):
    TRAINING_INVALIDATED = "training_invalidated"
    SCORING_INVALIDATED = "scoring_invalidated"
    THRESHOLD_INVALIDATED = "threshold_invalidated"
    EVALUATION_STATISTICS_INVALIDATED = "evaluation_statistics_invalidated"
    NO_OUTPUT_IMPACT = "no_output_impact"


def _contains_cycle(edges: tuple[tuple[str, str], ...]) -> bool:
    children_by_parent: dict[str, tuple[str, ...]] = {}
    for parent, child in edges:
        children_by_parent[parent] = (*children_by_parent.get(parent, ()), child)
    for origin in children_by_parent:
        pending = list(children_by_parent[origin])
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == origin:
                return True
            if current not in visited:
                visited.add(current)
                pending.extend(children_by_parent.get(current, ()))
    return False


@dataclass(frozen=True, slots=True, kw_only=True)
class StageDependency:
    upstream: StageFingerprint
    downstream: StageFingerprint

    def __post_init__(self) -> None:
        if self.upstream == self.downstream:
            raise DomainValidationError(
                detail="a stage dependency cannot depend on itself",
                value=repr(self),
                constraint="distinct upstream and downstream stage fingerprints",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class StageDependencyCollection:
    dependencies: tuple[StageDependency, ...]

    def __post_init__(self) -> None:
        edges = tuple((dependency.upstream.value, dependency.downstream.value) for dependency in self.dependencies)
        if len(set(edges)) != len(edges):
            raise DomainValidationError(
                detail="stage dependencies must be unique",
                value=repr(edges),
                constraint="unique ordered upstream/downstream pairs",
            )
        if _contains_cycle(edges):
            raise DomainValidationError(
                detail="stage dependency collection must not contain a cycle",
                value=repr(edges),
                constraint="acyclic stage dependency graph",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class StageFingerprintIdentity:
    value: StageFingerprint


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSourceIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureSchemaIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class PartitionIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class FittedPreprocessorIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessedSplitIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationScoringIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TestScoringIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalScoringIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticalIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ResultFreezeIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedModelIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedCheckpointIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedCalibrationScoringIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedTestScoringIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedThresholdIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedEvaluationIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalWindowIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedConfigurationIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryCompatibilityIdentity(StageFingerprintIdentity):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class StageIdentity:
    dataset_source: DatasetSourceIdentity
    feature_schema: FeatureSchemaIdentity
    partition: PartitionIdentity
    split: SplitIdentity
    fitted_preprocessor: FittedPreprocessorIdentity
    processed_split: ProcessedSplitIdentity
    training: TrainingIdentity
    checkpoint: CheckpointIdentity
    checkpoint_selection: CheckpointSelectionIdentity
    calibration_scoring: CalibrationScoringIdentity
    test_scoring: TestScoringIdentity
    temporal_scoring: TemporalScoringIdentity
    threshold: ThresholdIdentity
    evaluation: EvaluationIdentity
    statistical: StatisticalIdentity
    result_freeze: ResultFreezeIdentity
    report: ReportIdentity

    def __post_init__(self) -> None:
        expected_types = (
            DatasetSourceIdentity,
            FeatureSchemaIdentity,
            PartitionIdentity,
            SplitIdentity,
            FittedPreprocessorIdentity,
            ProcessedSplitIdentity,
            TrainingIdentity,
            CheckpointIdentity,
            CheckpointSelectionIdentity,
            CalibrationScoringIdentity,
            TestScoringIdentity,
            TemporalScoringIdentity,
            ThresholdIdentity,
            EvaluationIdentity,
            StatisticalIdentity,
            ResultFreezeIdentity,
            ReportIdentity,
        )
        values = (
            self.dataset_source,
            self.feature_schema,
            self.partition,
            self.split,
            self.fitted_preprocessor,
            self.processed_split,
            self.training,
            self.checkpoint,
            self.checkpoint_selection,
            self.calibration_scoring,
            self.test_scoring,
            self.temporal_scoring,
            self.threshold,
            self.evaluation,
            self.statistical,
            self.result_freeze,
            self.report,
        )
        if any(type(value) is not expected_type for value, expected_type in zip(values, expected_types, strict=True)):
            raise DomainValidationError(
                detail="stage identity requires one nominal identity for every pipeline lineage position",
                value=repr(self),
                constraint="complete ordered nominal stage-identity chain",
            )
