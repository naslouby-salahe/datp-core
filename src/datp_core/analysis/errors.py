"""Typed exception hierarchy for analysis-package domain failures."""

from __future__ import annotations


class AnalysisError(Exception):
    """Base exception for all analysis-package domain failures."""


class UnsupportedAnalysisError(AnalysisError):
    """The requested analysis kind has no registered implementation."""


class InvalidAnalysisConfigurationError(AnalysisError):
    """Analysis configuration is missing required values or contains invalid combinations."""


class ArtifactMissingError(AnalysisError):
    """A required artifact is unavailable at the expected path."""


class ArtifactSchemaViolationError(AnalysisError):
    """A loaded artifact does not conform to its expected schema."""


class PopulationAlignmentError(AnalysisError):
    """Client populations across compared artifacts do not align as required."""


class ScientificContractViolationError(AnalysisError):
    """A scientific invariant required by the protocol is violated."""


class PrerequisiteResultMissingError(AnalysisError, ValueError):
    """A prerequisite analysis result required for the current analysis is unavailable."""


class ResultEncodingError(AnalysisError):
    """An analysis result could not be encoded for persistence."""


class ResultDecodingError(AnalysisError):
    """A persisted analysis result could not be decoded to the expected type."""


class StatisticalProcedureError(AnalysisError):
    """A statistical procedure cannot produce a valid result."""


class AnalysisRegistrationError(AnalysisError):
    """Failure during analysis capability single-dispatch registration."""


class DuplicateAnalysisRegistrationError(AnalysisRegistrationError):
    """An analysis record type is registered more than once."""


class UnsupportedAnalysisRecordError(AnalysisRegistrationError):
    """An unsupported analysis record type was supplied to the runner."""


class ResultRegistryError(AnalysisError):
    """Failure during analysis result registry operation."""


class DuplicateResultKindError(ResultRegistryError):
    """An analysis result kind is registered more than once."""


class DuplicateResultTypeError(ResultRegistryError):
    """An analysis result class is registered more than once."""


class UnsupportedPayloadVersionError(ResultRegistryError):
    """A result payload version is unsupported by the codec."""


class UnknownResultKindError(ResultRegistryError):
    """An unrecognized result kind was encountered by the registry or codec."""
