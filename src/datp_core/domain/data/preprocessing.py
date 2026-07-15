from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FittedPreprocessorIdentity, SplitIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.data.splitting import TrainingSplitSpec
from datp_core.domain.errors import DomainValidationError
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
