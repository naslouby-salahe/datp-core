from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FeatureSchemaIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.errors import DomainValidationError


class Dataset(StrEnum):
    N_BAIOT = "n_baiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


class Regime(StrEnum):
    A = "a"
    B_A = "b_a"
    C = "c"
    D = "d"
    D_TEMPORAL = "d_temporal"


class TimestampEvidenceKind(StrEnum):
    GENUINE_CAPTURE_TIME = "genuine_capture_time"


def _validated_timestamp_field(value: str) -> None:
    if not value:
        raise DomainValidationError(
            detail="capture timestamp evidence requires a field name", value=repr(value), constraint="non-empty"
        )
    if any(character.isspace() for character in value):
        raise DomainValidationError(
            detail="capture timestamp evidence must not contain whitespace",
            value=repr(value),
            constraint="no whitespace",
        )
    _validated_not_pseudo_time(value)


def _validated_not_pseudo_time(value: str) -> None:
    if any(marker in value.casefold() for marker in ("file", "row", "merge", "directory", "synthetic", "order")):
        raise DomainValidationError(
            detail="timestamp evidence must name genuine capture time",
            value=repr(value),
            constraint="genuine capture-time field",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSpec:
    dataset: Dataset
    input_dim: int
    feature_schema_identity: FeatureSchemaIdentity
    feature_count_verified: bool

    def __post_init__(self) -> None:
        if isinstance(self.input_dim, bool) or self.input_dim < 1:
            raise DomainValidationError(
                detail="dataset input dimension must be a positive integer",
                value=repr(self.input_dim),
                constraint="input dimension >= 1",
            )
        if self.dataset is Dataset.CICIOT2023 and not self.feature_count_verified:
            raise DomainValidationError(
                detail="CICIoT2023 requires verified feature count",
                value=repr(self.feature_count_verified),
                constraint="CICIoT2023 feature count verified",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TimestampEvidence:
    kind: TimestampEvidenceKind
    capture_timestamp_field: str

    def __post_init__(self) -> None:
        if self.kind is not TimestampEvidenceKind.GENUINE_CAPTURE_TIME:
            raise DomainValidationError(
                detail="timestamp evidence must be classified as genuine capture time",
                value=repr(self.kind),
                constraint="GENUINE_CAPTURE_TIME",
            )
        _validated_timestamp_field(self.capture_timestamp_field)


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSourceInspectionResult:
    source_manifest: ArtifactRef
    feature_schema_manifest: ArtifactRef
    source_row_identity: DatasetSourceIdentity
    timestamp_evidence: TimestampEvidence | None
