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
    ProtocolValidationError,
    ReportEvidenceError,
    ScientificContractError,
    UnknownIdentifierError,
)

type CliHandledError = DatpCoreError | ValueError


def map_exception_to_exit(error: CliHandledError) -> int: #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    if isinstance(error, MissingPrerequisiteError):
        if error.reason == "anchor_gate":
            return CliExitCode.ANCHOR_GATE_FAILURE.value
        return CliExitCode.INCOMPLETE_PREREQUISITE.value
    if isinstance(error, UnknownIdentifierError):
        return CliExitCode.UNKNOWN_IDENTIFIER.value
    if isinstance(error, ProtocolValidationError):
        return CliExitCode.INVALID_DECLARATION.value
    if isinstance(error, ReportEvidenceError):
        return CliExitCode.MISSING_REPORT_EVIDENCE.value
    if isinstance(error, ArtifactIntegrityError):
        return CliExitCode.INVALID_ARTIFACT.value
    if isinstance(error, AnchorReproductionError):
        return CliExitCode.ANCHOR_GATE_FAILURE.value
    if isinstance(error, ScientificContractError):
        return CliExitCode.SCIENTIFIC_CONTRACT.value
    if isinstance(error, ValueError):
        return CliExitCode.USAGE.value
    return CliExitCode.INTERNAL.value


def fail(error: CliHandledError) -> Never:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=map_exception_to_exit(error)) from error
