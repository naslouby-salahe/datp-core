from __future__ import annotations

from typing import Annotated

import typer

from datp_core.app.cli.validation import fail
from datp_core.app.contracts import OverwriteMode, ProgrammeExecutionMode
from datp_core.app.research import format_experiment_completion, run_campaign, run_experiment
from datp_core.core.errors import DatpCoreError
from datp_core.core.identifiers import ExperimentId

app = typer.Typer(no_args_is_help=True, help="Run one experiment or the complete campaign.")


def _overwrite_mode(overwrite: bool) -> OverwriteMode:
    return OverwriteMode.REBUILD if overwrite else OverwriteMode.KEEP_EXISTING


@app.command("experiment")
def experiment_command(
    experiment_id: Annotated[ExperimentId, typer.Argument(case_sensitive=False)],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild this experiment's owned artifacts"),
    ] = False,
) -> None:
    try:
        result = run_experiment(
            experiment_id,
            overwrite=_overwrite_mode(overwrite),
            mode=ProgrammeExecutionMode.FULL,
        )
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(format_experiment_completion(result))
    if result.method_outcomes:
        outcomes = ",".join(f"{item.method.value}={item.status.value}" for item in result.method_outcomes)
        typer.echo(f"methods={outcomes}")


@app.command("campaign")
def campaign_command(
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild campaign-owned execution and analysis artifacts"),
    ] = False,
) -> None:
    try:
        result = run_campaign(overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"campaign experiments={len(result.experiments)} detail={result.detail}")
