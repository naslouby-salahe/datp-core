"""Generic experiment and campaign execution commands."""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.app.cli.validation import fail
from datp_core.app.contracts import OverwriteMode, ProgrammeExecutionMode
from datp_core.app.research import run_campaign, run_experiment
from datp_core.domain.enums import ExperimentId
from datp_core.domain.errors import DatpCoreError

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
    """Run one experiment's complete declared recipe and full seed cohort."""
    try:
        result = run_experiment(
            experiment_id,
            overwrite=_overwrite_mode(overwrite),
            mode=ProgrammeExecutionMode.FULL,
        )
    except (DatpCoreError, ValueError) as error:
        fail(error)
    outcomes = ",".join(f"{item.method.value}={item.status.value}" for item in result.method_outcomes)
    typer.echo(
        f"experiment={result.experiment.value} seeds={len(result.seeds)} "
        f"output_root={result.output_root} detail={result.detail} methods={outcomes}"
    )


@app.command("campaign")
def campaign_command(
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild campaign-owned execution and analysis artifacts"),
    ] = False,
) -> None:
    """Run the complete scientific programme in deterministic dependency order."""
    try:
        result = run_campaign(overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"campaign experiments={len(result.experiments)} detail={result.detail}")
