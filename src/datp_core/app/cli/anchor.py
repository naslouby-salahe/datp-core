"""Anchor reproduction, verification, and status commands."""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.app.cli.validation import fail
from datp_core.app.contracts import OverwriteMode, ProgrammeExecutionMode
from datp_core.app.research import anchor_status, reproduce_anchor, verify_anchor_programme
from datp_core.domain.errors import DatpCoreError

app = typer.Typer(no_args_is_help=True, help="Historical anchor equivalence gate.")


def _overwrite_mode(overwrite: bool) -> OverwriteMode:
    return OverwriteMode.REBUILD if overwrite else OverwriteMode.KEEP_EXISTING


@app.command("reproduce")
def reproduce_command(
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild independent anchor reproduction only"),
    ] = False,
) -> None:
    """Run independent anchor reproduction for the declared historical seed cohort."""
    try:
        result = reproduce_anchor(
            overwrite=_overwrite_mode(overwrite),
            mode=ProgrammeExecutionMode.FULL,
        )
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"gate={result.gate_status.value} readiness={result.dependent_readiness.value} detail={result.detail}")


@app.command("verify")
def verify_command() -> None:
    """Verify independent anchor reproduction against locked historical references."""
    try:
        result = verify_anchor_programme(mode=ProgrammeExecutionMode.FULL)
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"gate={result.gate_status.value} readiness={result.dependent_readiness.value} detail={result.detail}")


@app.command("status")
def status_command() -> None:
    """Show anchor reference, reproduction, comparison, and dependent readiness."""
    try:
        result = anchor_status()
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"gate={result.gate_status.value} readiness={result.dependent_readiness.value} detail={result.detail}")
