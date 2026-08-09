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

_EXIT_CODES: dict[type[Exception], CliExitCode] = {
    UnknownIdentifierError: CliExitCode.UNKNOWN_IDENTIFIER,
    ProtocolValidationError: CliExitCode.INVALID_DECLARATION,
    ReportEvidenceError: CliExitCode.MISSING_REPORT_EVIDENCE,
    ArtifactIntegrityError: CliExitCode.INVALID_ARTIFACT,
    AnchorReproductionError: CliExitCode.ANCHOR_GATE_FAILURE,
    ScientificContractError: CliExitCode.SCIENTIFIC_CONTRACT,
    ValueError: CliExitCode.USAGE,
}


def map_exception_to_exit(error: CliHandledError) -> CliExitCode:
    if isinstance(error, MissingPrerequisiteError):
        if (
            isinstance(error.reason, MissingPrerequisiteReason)
            and error.reason is MissingPrerequisiteReason.ANCHOR_GATE
        ):
            return CliExitCode.ANCHOR_GATE_FAILURE
        return CliExitCode.INCOMPLETE_PREREQUISITE
    for error_type in type(error).__mro__:
        exit_code = _EXIT_CODES.get(error_type)
        if exit_code is not None:
            return exit_code
    return CliExitCode.INTERNAL


def fail(error: CliHandledError) -> Never:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=map_exception_to_exit(error).value) from error
