from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FittedPreprocessorIdentity, SplitIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.data.splitting import TrainingSplitSpec
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.admissibility import ChunkRowCount


class NormalizationStrategy(StrEnum):
    MIN_MAX = "min_max"
    STANDARD = "standard"
    ROBUST = "robust"
    NONE = "none"


class NormalizationScope(StrEnum):
    GLOBAL_TRAIN = "global_train"
    PER_CLIENT_TRAIN = "per_client_train"


class FittedStatisticPolicy(StrEnum):
    EXACT_TWO_PASS = "exact_two_pass"
    INCREMENTAL = "incremental"


def validate_train_fit_split(*, split: object) -> TrainingSplitSpec:
    if type(split) is not TrainingSplitSpec:
        raise DomainValidationError(
            detail="preprocessing fit authorization requires the TRAIN split",
            value=type(split).__name__,
            constraint="TrainingSplitSpec",
        )
    return split


@dataclass(frozen=True, slots=True, kw_only=True)
class PreprocessingChunkSpec:
    source_scan_batch_rows: ChunkRowCount
    preprocessing_chunk_rows: ChunkRowCount
    parquet_write_batch_rows: ChunkRowCount


@dataclass(frozen=True, slots=True, kw_only=True)
class PreprocessingSpec:
    strategy: NormalizationStrategy
    scope: NormalizationScope
    fitted_stat_policy: FittedStatisticPolicy
    chunking: PreprocessingChunkSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class FittedPreprocessorResult:
    artifact: ArtifactRef
    identity: FittedPreprocessorIdentity
    training_row_order_checksum: str

    def __post_init__(self) -> None:
        if not self.training_row_order_checksum:
            raise DomainValidationError(
                detail="fitted preprocessor requires a training row-order checksum",
                value=repr(self.training_row_order_checksum),
                constraint="non-empty training row-order checksum",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessedSplitResult:
    artifacts: tuple[ArtifactRef, ...]
    split_manifest_identity: SplitIdentity
    preprocessor_identity: FittedPreprocessorIdentity
    source_row_lineage: tuple[DatasetSourceIdentity, ...]

    def __post_init__(self) -> None:
        if not self.artifacts:
            raise DomainValidationError(
                detail="processed split result requires at least one artifact",
                value=repr(self.artifacts),
                constraint="non-empty processed split artifacts",
            )
        if not self.source_row_lineage:
            raise DomainValidationError(
                detail="processed split result requires source row lineage",
                value=repr(self.source_row_lineage),
                constraint="non-empty source row lineage",
            )


def _validated_finite(value: float, *, name: str) -> None:
    if not isfinite(value):
        raise DomainValidationError(detail=f"{name} must be finite", value=repr(value), constraint="finite value")


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureStatistics:
    feature: str
    mean: float
    variance: float

    def __post_init__(self) -> None:
        if not self.feature:
            raise DomainValidationError(
                detail="feature statistics require a non-empty feature name",
                value=repr(self.feature),
                constraint="non-empty feature name",
            )
        _validated_finite(self.mean, name="feature mean")
        _validated_finite(self.variance, name="feature variance")
        if self.variance < 0:
            raise DomainValidationError(
                detail="feature variance must be non-negative",
                value=repr(self.variance),
                constraint="variance >= 0",
            )


def _validated_client_statistics_present(feature_columns: tuple[str, ...]) -> None:
    if not feature_columns:
        raise DomainValidationError(
            detail="client feature statistics require at least one feature column",
            value=repr(feature_columns),
            constraint="non-empty feature columns",
        )


def _validated_statistics_match_feature_columns(
    *, statistics: tuple[FeatureStatistics, ...], feature_columns: tuple[str, ...]
) -> None:
    statistic_features = tuple(entry.feature for entry in statistics)
    if statistic_features != feature_columns:
        raise DomainValidationError(
            detail="client feature statistics must cover exactly the declared feature columns, in order",
            value=repr(statistic_features),
            constraint="statistics feature order == feature_columns",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientFeatureStatistics:
    client_id: ClientId
    feature_columns: tuple[str, ...]
    statistics: tuple[FeatureStatistics, ...]
    training_row_count: int
    training_row_order_checksum: str

    def __post_init__(self) -> None:
        _validated_client_statistics_present(self.feature_columns)
        _validated_statistics_match_feature_columns(statistics=self.statistics, feature_columns=self.feature_columns)
        if isinstance(self.training_row_count, bool) or self.training_row_count < 1:
            raise DomainValidationError(
                detail="client feature statistics require a positive training row count",
                value=repr(self.training_row_count),
                constraint="training row count >= 1",
            )
        if not self.training_row_order_checksum:
            raise DomainValidationError(
                detail="client feature statistics require a non-empty training row-order checksum",
                value=repr(self.training_row_order_checksum),
                constraint="non-empty training row-order checksum",
            )


def _validated_unique_client_statistics(client_statistics: tuple[ClientFeatureStatistics, ...]) -> None:
    client_ids = tuple(entry.client_id.value for entry in client_statistics)
    if not client_ids or len(set(client_ids)) != len(client_ids):
        raise DomainValidationError(
            detail="fitted preprocessor manifest requires at least one client with unique client ids",
            value=repr(client_ids),
            constraint="non-empty unique client ids",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class FittedPreprocessorManifest:
    strategy: NormalizationStrategy
    scope: NormalizationScope
    feature_columns: tuple[str, ...]
    client_statistics: tuple[ClientFeatureStatistics, ...]

    def __post_init__(self) -> None:
        if self.scope is not NormalizationScope.PER_CLIENT_TRAIN:
            raise DomainValidationError(
                detail="the fitted preprocessor scope is per-client TRAIN only",
                value=self.scope.value,
                constraint="PER_CLIENT_TRAIN",
            )
        _validated_unique_client_statistics(self.client_statistics)
