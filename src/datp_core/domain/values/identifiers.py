"""Validated identifier strings and their immutable typed sequences."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.domain.values.base import (
    _NonEmptyString,
    _validate_unique,
    sequence_pydantic_schema,
    validate_non_empty_tuple,
)


class FeatureName(_NonEmptyString):
    validation_name: ClassVar[str] = "feature name"


class OutcomeLabel(_NonEmptyString):
    validation_name: ClassVar[str] = "outcome label"


class StableRowId(_NonEmptyString):
    """An opaque `relative_source_path:row_index` identity token; the embedded
    source path may legitimately contain path separators for nested source files."""

    validation_name: ClassVar[str] = "stable row ID"


class CaptureTimestampColumn(_NonEmptyString):
    validation_name: ClassVar[str] = "capture timestamp column"


class SafeTensorFilename(_NonEmptyString):
    validation_name: ClassVar[str] = "SafeTensors filename"

    def __new__(cls, value: str) -> "SafeTensorFilename":
        instance = super().__new__(cls, value)
        if not instance.endswith(".safetensors"):
            raise ValueError("SafeTensors filename must end with .safetensors")
        return instance


class CudaDeviceName(_NonEmptyString):
    validation_name: ClassVar[str] = "CUDA device name"

    def __new__(cls, value: str) -> "CudaDeviceName":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("CUDA device name must be a non-empty string")
        return str.__new__(cls, value)


@dataclass(frozen=True, slots=True)
class FeatureNameSequence:
    names: tuple[FeatureName, ...]

    def __post_init__(self) -> None:
        wrapped = tuple(item if isinstance(item, FeatureName) else FeatureName(item) for item in self.names)
        object.__setattr__(self, "names", wrapped)
        validate_non_empty_tuple(self.names, "feature name sequence")
        _validate_unique(self.names, "feature names")

    def __len__(self) -> int:
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def as_list(self) -> list[str]:
        return list(self.names)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)


@dataclass(frozen=True, slots=True)
class OutcomeLabelSequence:
    labels: tuple[OutcomeLabel, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.labels, tuple):
            raise TypeError("outcome labels must be an immutable tuple")
        object.__setattr__(
            self,
            "labels",
            tuple(item if isinstance(item, OutcomeLabel) else OutcomeLabel(item) for item in self.labels),
        )

    def __len__(self) -> int:
        return len(self.labels)

    def __iter__(self):
        return iter(self.labels)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)


@dataclass(frozen=True, slots=True)
class StableRowIdSequence:
    row_ids: tuple[StableRowId, ...]

    def __post_init__(self) -> None:
        wrapped = tuple(item if isinstance(item, StableRowId) else StableRowId(item) for item in self.row_ids)
        object.__setattr__(self, "row_ids", wrapped)
        validate_non_empty_tuple(self.row_ids, "stable row ID sequence")
        _validate_unique(self.row_ids, "stable row IDs")

    def __len__(self) -> int:
        return len(self.row_ids)

    def __iter__(self):
        return iter(self.row_ids)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)
