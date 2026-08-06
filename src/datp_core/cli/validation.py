"""CLI presentation helpers and typed exit-code mapping."""

from __future__ import annotations

import typer

from datp_core.domain.errors import (
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

_EXIT_BY_TYPE: tuple[tuple[type[BaseException], int], ...] = (
    (UnknownIdentifierError, CliExitCode.UNKNOWN_IDENTIFIER.value),
    (ProtocolValidationError, CliExitCode.INVALID_DECLARATION.value),
    (ReportEvidenceError, CliExitCode.MISSING_REPORT_EVIDENCE.value),
    (ArtifactIntegrityError, CliExitCode.INVALID_ARTIFACT.value),
    (AnchorReproductionError, CliExitCode.ANCHOR_GATE_FAILURE.value),
    (ScientificContractError, CliExitCode.SCIENTIFIC_CONTRACT.value),
    (ValueError, CliExitCode.USAGE.value),
)


def echo_lines(lines: tuple[str, ...]) -> None:
    for line in lines:
        typer.echo(line)


def echo_error(error: BaseException) -> None:
    typer.echo(str(error), err=True)


def map_exception_to_exit(error: BaseException) -> int:
    if isinstance(error, typer.Exit):
        return int(error.exit_code)
    if isinstance(error, MissingPrerequisiteError):
        if error.reason == "anchor_gate":
            return CliExitCode.ANCHOR_GATE_FAILURE.value
        return CliExitCode.INCOMPLETE_PREREQUISITE.value
    for error_type, code in _EXIT_BY_TYPE:
        if isinstance(error, error_type):
            return code
    if isinstance(error, DatpCoreError):
        return CliExitCode.INTERNAL.value
    return CliExitCode.INTERNAL.value
