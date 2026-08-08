"""Anchor reproduction, verification, and status commands."""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.app.cli.validation import echo_error, map_exception_to_exit
from datp_core.app.programme import anchor_status, reproduce_anchor, verify_anchor_programme

app = typer.Typer(no_args_is_help=True, help="Historical anchor equivalence gate.")


@app.command("reproduce")
def reproduce_command(
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild independent anchor reproduction only"),
    ] = False,
) -> None:
    """Run independent anchor reproduction for the declared historical seed cohort."""
    try:
        result = reproduce_anchor(overwrite=overwrite, smoke=False)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(f"gate={result.gate_status} readiness={result.dependent_readiness} detail={result.detail}")


@app.command("verify")
def verify_command() -> None:
    """Verify independent anchor reproduction against locked historical references."""
    try:
        result = verify_anchor_programme(smoke=False)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(f"gate={result.gate_status} readiness={result.dependent_readiness} detail={result.detail}")


@app.command("status")
def status_command() -> None:
    """Show anchor reference, reproduction, comparison, and dependent readiness."""
    try:
        result = anchor_status()
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(f"gate={result.gate_status} readiness={result.dependent_readiness} detail={result.detail}")
