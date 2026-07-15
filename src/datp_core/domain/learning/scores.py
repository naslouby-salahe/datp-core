from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from typing import TYPE_CHECKING

from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
    CheckpointIdentity,
    DatasetSourceIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    PartitionIdentity,
    SplitIdentity,
    TemporalScoringIdentity,
    TemporalWindowIdentity,
    TestScoringIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.references import (
    ArtifactRef,
    ArtifactSchemaVersion,
    CalibrationScoreArtifactId,
    TemporalScoreArtifactId,
    TestScoreArtifactId,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.training import PrecisionMode
from datp_core.domain.runtime.admissibility import BatchSize

if TYPE_CHECKING:
    from datp_core.domain.thresholding.policies import ThresholdValue

_CONTENT_HASH_PATTERN = r"[0-9a-f]{64}"


class QuantileEstimatorType(StrEnum):
    LOCAL_EXACT = "local_exact"
    POOLED_EXACT = "pooled_exact"
    WEIGHTED_EXACT = "weighted_exact"
    CENTRALIZED_ORACLE = "centralized_oracle"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientRoster:
    client_ids: tuple[ClientId, ...]

    def __post_init__(self) -> None:
        values = tuple(client_id.value for client_id in self.client_ids)
        if not _is_canonical_client_roster(values):
            raise DomainValidationError(
                detail="client roster must be non-empty, unique, and canonically ordered",
                value=repr(values),
                constraint="non-empty unique lexicographically ordered client ids",
            )


def _is_canonical_client_roster(values: tuple[str, ...]) -> bool:
    return bool(values) and len(set(values)) == len(values) and values == tuple(sorted(values))


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientMapEntry[ClientValue]:
    client_id: ClientId
    value: ClientValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientMap[ClientValue]:
    roster: ClientRoster
    entries: tuple[ClientMapEntry[ClientValue], ...]

    def __post_init__(self) -> None:
        roster_ids = self.roster.client_ids
        entry_ids = tuple(entry.client_id for entry in self.entries)
        if entry_ids != roster_ids:
            raise DomainValidationError(
                detail="client map entries must match the roster exactly in canonical order",
                value=repr(entry_ids),
                constraint="one ordered entry for every roster client",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientCalibrationScoreMap[ScoreValue]:
    values: ClientMap[ScoreValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientTestScoreMap[ScoreValue]:
    values: ClientMap[ScoreValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientTemporalScoreMap[ScoreValue]:
    values: ClientMap[ScoreValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientEvaluationMap[EvaluationValue]:
    values: ClientMap[EvaluationValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdAssignmentSet:
    values: ClientMap[ThresholdValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoringBatchSpec:
    calibration_batch_size: BatchSize
    test_batch_size: BatchSize
    temporal_batch_size: BatchSize

    def __post_init__(self) -> None:
        if any(
            type(batch_size) is not BatchSize
            for batch_size in (self.calibration_batch_size, self.test_batch_size, self.temporal_batch_size)
        ):
            raise DomainValidationError(
                detail="scoring batch specification requires typed batch sizes",
                value=repr(self),
                constraint="BatchSize for calibration, test, and temporal scoring",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreSampleCount:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise DomainValidationError(
                detail="score sample count must be a non-negative integer",
                value=repr(self.value),
                constraint="integer >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreGenerationSpec:
    scoring_batch: ScoringBatchSpec
    precision: PrecisionMode
    numeric_equivalence_policy: str

    def __post_init__(self) -> None:
        if not _is_valid_score_generation_specification(self):
            raise DomainValidationError(
                detail="score generation requires typed batching, precision, and numeric equivalence policy",
                value=repr(self),
                constraint="ScoringBatchSpec, PrecisionMode, non-empty equivalence policy",
            )


def _is_valid_score_generation_specification(specification: ScoreGenerationSpec) -> bool:
    return all(
        (
            type(specification.scoring_batch) is ScoringBatchSpec,
            type(specification.precision) is PrecisionMode,
            type(specification.numeric_equivalence_policy) is str,
            bool(specification.numeric_equivalence_policy),
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientCalibrationScoreArtifact:
    client_id: ClientId
    calibration_split_identity: SplitIdentity
    split_manifest_hash: str
    scoring_identity: CalibrationScoringIdentity
    scientific_checkpoint_identity: CheckpointIdentity
    scientific_checkpoint_content_hash: str
    fitted_preprocessor_identity: FittedPreprocessorIdentity
    feature_schema_identity: FeatureSchemaIdentity
    sample_count: ScoreSampleCount
    schema_version: ArtifactSchemaVersion
    content_hash: str
    row_order_checksum: str
    artifact_ref: ArtifactRef

    def __post_init__(self) -> None:
        if not _is_valid_calibration_score_artifact(self):
            raise DomainValidationError(
                detail="calibration score artifact requires complete typed integrity-bound lineage",
                value=repr(self),
                constraint="typed calibration fields, valid checksums, and matching reference hash",
            )


def _is_valid_calibration_score_artifact(artifact: ClientCalibrationScoreArtifact) -> bool:
    return all(
        (
            _has_calibration_score_artifact_types(artifact),
            _are_valid_content_hashes(
                artifact.split_manifest_hash,
                artifact.scientific_checkpoint_content_hash,
                artifact.content_hash,
            ),
            bool(artifact.row_order_checksum),
            artifact.artifact_ref.content_hash == artifact.content_hash,
        )
    )


def _has_calibration_score_artifact_types(artifact: ClientCalibrationScoreArtifact) -> bool:
    return all(
        (
            type(artifact.client_id) is ClientId,
            type(artifact.calibration_split_identity) is SplitIdentity,
            type(artifact.scoring_identity) is CalibrationScoringIdentity,
            type(artifact.scientific_checkpoint_identity) is CheckpointIdentity,
            type(artifact.fitted_preprocessor_identity) is FittedPreprocessorIdentity,
            type(artifact.feature_schema_identity) is FeatureSchemaIdentity,
            type(artifact.sample_count) is ScoreSampleCount,
            type(artifact.schema_version) is ArtifactSchemaVersion,
            type(artifact.artifact_ref) is ArtifactRef,
        )
    )


def _are_valid_content_hashes(*values: str) -> bool:
    return all(fullmatch(_CONTENT_HASH_PATTERN, value) is not None for value in values)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientTestScoreArtifact:
    client_id: ClientId
    test_split_identity: SplitIdentity
    split_manifest_hash: str
    test_scoring_identity: TestScoringIdentity
    scientific_checkpoint_identity: CheckpointIdentity
    scientific_checkpoint_content_hash: str
    fitted_preprocessor_identity: FittedPreprocessorIdentity
    feature_schema_identity: FeatureSchemaIdentity
    benign_scores_ref: ArtifactRef
    benign_sample_count: ScoreSampleCount
    benign_content_hash: str
    benign_row_order_checksum: str
    attack_scores_ref: ArtifactRef
    attack_sample_count: ScoreSampleCount
    attack_content_hash: str
    attack_row_order_checksum: str
    aggregate_manifest_hash: str
    score_schema_version: ArtifactSchemaVersion

    def __post_init__(self) -> None:
        if not _is_valid_test_score_artifact(self):
            raise DomainValidationError(
                detail="test score artifact requires complete typed integrity-bound lineage",
                value=repr(self),
                constraint="typed test fields, valid checksums, and matching child hashes",
            )


def _is_valid_test_score_artifact(artifact: ClientTestScoreArtifact) -> bool:
    return all(
        (
            _has_test_score_artifact_types(artifact),
            _are_valid_content_hashes(
                artifact.split_manifest_hash,
                artifact.scientific_checkpoint_content_hash,
                artifact.benign_content_hash,
                artifact.attack_content_hash,
                artifact.aggregate_manifest_hash,
            ),
            bool(artifact.benign_row_order_checksum),
            bool(artifact.attack_row_order_checksum),
            artifact.benign_scores_ref.content_hash == artifact.benign_content_hash,
            artifact.attack_scores_ref.content_hash == artifact.attack_content_hash,
        )
    )


def _has_test_score_artifact_types(artifact: ClientTestScoreArtifact) -> bool:
    return all(
        (
            type(artifact.client_id) is ClientId,
            type(artifact.test_split_identity) is SplitIdentity,
            type(artifact.test_scoring_identity) is TestScoringIdentity,
            type(artifact.scientific_checkpoint_identity) is CheckpointIdentity,
            type(artifact.fitted_preprocessor_identity) is FittedPreprocessorIdentity,
            type(artifact.feature_schema_identity) is FeatureSchemaIdentity,
            type(artifact.benign_scores_ref) is ArtifactRef,
            type(artifact.attack_scores_ref) is ArtifactRef,
            type(artifact.benign_sample_count) is ScoreSampleCount,
            type(artifact.attack_sample_count) is ScoreSampleCount,
            type(artifact.score_schema_version) is ArtifactSchemaVersion,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientTemporalScoreArtifact:
    test_artifact: ClientTestScoreArtifact
    temporal_window_identity: TemporalWindowIdentity
    boundary_identity: TemporalWindowIdentity

    def __post_init__(self) -> None:
        if type(self.test_artifact) is not ClientTestScoreArtifact:
            raise DomainValidationError(
                detail="temporal score artifact requires typed test-score lineage",
                value=repr(self.test_artifact),
                constraint="ClientTestScoreArtifact",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreLineageContext:
    dataset_source_identity: DatasetSourceIdentity
    partition_identity: PartitionIdentity
    split_identity: SplitIdentity
    scientific_checkpoint_identity: CheckpointIdentity
    scientific_checkpoint_content_hash: str
    fitted_preprocessor_identity: FittedPreprocessorIdentity
    feature_schema_identity: FeatureSchemaIdentity
    training_identity: TrainingIdentity
    score_schema_version: ArtifactSchemaVersion
    roster: ClientRoster
    row_order_checksum: str
    precision: PrecisionMode
    scoring_batch_size: BatchSize

    def __post_init__(self) -> None:
        if not _is_valid_score_lineage_context(self):
            raise DomainValidationError(
                detail="score lineage context requires complete typed score compatibility evidence",
                value=repr(self),
                constraint=(
                    "source, partition, split, checkpoint, preprocessing, schema, training, roster, order, "
                    "precision, and batch"
                ),
            )


def _is_valid_score_lineage_context(context: ScoreLineageContext) -> bool:
    return all(
        (
            type(context.dataset_source_identity) is DatasetSourceIdentity,
            type(context.partition_identity) is PartitionIdentity,
            type(context.split_identity) is SplitIdentity,
            type(context.scientific_checkpoint_identity) is CheckpointIdentity,
            _are_valid_content_hashes(context.scientific_checkpoint_content_hash),
            type(context.fitted_preprocessor_identity) is FittedPreprocessorIdentity,
            type(context.feature_schema_identity) is FeatureSchemaIdentity,
            type(context.training_identity) is TrainingIdentity,
            type(context.score_schema_version) is ArtifactSchemaVersion,
            type(context.roster) is ClientRoster,
            type(context.row_order_checksum) is str,
            bool(context.row_order_checksum),
            type(context.precision) is PrecisionMode,
            type(context.scoring_batch_size) is BatchSize,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationScoringLineage:
    scoring_identity: CalibrationScoringIdentity
    context: ScoreLineageContext


@dataclass(frozen=True, slots=True, kw_only=True)
class TestScoringLineage:
    scoring_identity: TestScoringIdentity
    context: ScoreLineageContext


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalScoringLineage:
    scoring_identity: TemporalScoringIdentity
    context: ScoreLineageContext


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationScoreArtifactSet:
    artifact_id: CalibrationScoreArtifactId
    lineage: CalibrationScoringLineage
    per_client: ClientCalibrationScoreMap[ClientCalibrationScoreArtifact]

    def __post_init__(self) -> None:
        if not _is_valid_calibration_score_set(self):
            raise DomainValidationError(
                detail="calibration score set requires calibration-specific identity and lineage",
                value=repr(self),
                constraint="CalibrationScoreArtifactId and CalibrationScoringLineage",
            )


def _is_valid_calibration_score_set(score_set: CalibrationScoreArtifactSet) -> bool:
    return (
        type(score_set.artifact_id) is CalibrationScoreArtifactId
        and type(score_set.lineage) is CalibrationScoringLineage
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class TestScoreArtifactSet:
    artifact_id: TestScoreArtifactId
    lineage: TestScoringLineage
    per_client: ClientTestScoreMap[ClientTestScoreArtifact]

    def __post_init__(self) -> None:
        if not _is_valid_test_score_set(self):
            raise DomainValidationError(
                detail="test score set requires test-specific identity and lineage",
                value=repr(self),
                constraint="TestScoreArtifactId and TestScoringLineage",
            )


def _is_valid_test_score_set(score_set: TestScoreArtifactSet) -> bool:
    return type(score_set.artifact_id) is TestScoreArtifactId and type(score_set.lineage) is TestScoringLineage


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalScoreArtifactSet:
    artifact_id: TemporalScoreArtifactId
    lineage: TemporalScoringLineage
    window_identity: TemporalWindowIdentity
    per_client: ClientTemporalScoreMap[ClientTemporalScoreArtifact]

    def __post_init__(self) -> None:
        if not _is_valid_temporal_score_set(self):
            raise DomainValidationError(
                detail="temporal score set requires temporal-specific identity, lineage, and window",
                value=repr(self),
                constraint="TemporalScoreArtifactId, TemporalScoringLineage, and TemporalWindowIdentity",
            )


def _is_valid_temporal_score_set(score_set: TemporalScoreArtifactSet) -> bool:
    return all(
        (
            type(score_set.artifact_id) is TemporalScoreArtifactId,
            type(score_set.lineage) is TemporalScoringLineage,
            type(score_set.window_identity) is TemporalWindowIdentity,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitScopedScoreBundle:
    calibration: CalibrationScoreArtifactSet
    test: TestScoreArtifactSet
    temporal: TemporalScoreArtifactSet | None
