"""Validated identifiers.  Their syntax intentionally excludes file paths."""

from __future__ import annotations

from dataclasses import dataclass


def _validate_identifier(value: str) -> None:
    if not value or value.strip() != value or not value.strip():
        raise ValueError("identifier must be non-empty and canonical")
    if any(character in value for character in ("/", "\\", "\x00")):
        raise ValueError("identifier must not be path-like")


@dataclass(frozen=True, slots=True, order=True)
class _Identifier:
    value: str

    def __post_init__(self) -> None:
        _validate_identifier(self.value)

    def __str__(self) -> str:
        return self.value


class DatasetId(_Identifier):
    pass


class PopulationId(_Identifier):
    pass


class ExperimentId(_Identifier):
    pass


class EvaluationId(_Identifier):
    pass


class AnalysisId(_Identifier):
    pass


class ClientId(_Identifier):
    pass


class RunId(_Identifier):
    pass


class JobId(_Identifier):
    pass


class ArtifactId(_Identifier):
    pass


@dataclass(frozen=True, slots=True, order=True)
class RegistryId[TDefinition]:
    value: str

    def __post_init__(self) -> None:
        _validate_identifier(self.value)

    def __str__(self) -> str:
        return self.value
