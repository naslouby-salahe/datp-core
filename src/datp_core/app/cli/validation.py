"""CLI presentation helpers and typed exit-code mapping."""

from __future__ import annotations

from typing import Never

import typer

from datp_core.core.errors import (
    AnchorReproductionError,
    ArtifactIntegrityError,
    CliExitCode,
    DatpCoreError,
    MissingPrerequisiteError,
    MissingPrerequisiteReason,
    ProtocolValidationError,
    ReportEvidenceError,
    ScientificContractError,
    UnknownIdentifierError,
)

type CliHandledError = DatpCoreError | ValueError


def map_exception_to_exit(error: CliHandledError) -> CliExitCode:
    if isinstance(error, MissingPrerequisiteError):
        if (
            isinstance(error.reason, MissingPrerequisiteReason)
            and error.reason is MissingPrerequisiteReason.ANCHOR_GATE
        ):
            return CliExitCode.ANCHOR_GATE_FAILURE
        return CliExitCode.INCOMPLETE_PREREQUISITE
    if isinstance(error, UnknownIdentifierError):
        return CliExitCode.UNKNOWN_IDENTIFIER
    if isinstance(error, ProtocolValidationError):
        return CliExitCode.INVALID_DECLARATION
    if isinstance(error, ReportEvidenceError):
        return CliExitCode.MISSING_REPORT_EVIDENCE
    if isinstance(error, ArtifactIntegrityError):
        return CliExitCode.INVALID_ARTIFACT
    if isinstance(error, AnchorReproductionError):
        return CliExitCode.ANCHOR_GATE_FAILURE
    if isinstance(error, ScientificContractError):
        return CliExitCode.SCIENTIFIC_CONTRACT
    if isinstance(error, ValueError):
        return CliExitCode.USAGE
    return CliExitCode.INTERNAL


def fail(error: CliHandledError) -> Never:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=map_exception_to_exit(error).value) from error
