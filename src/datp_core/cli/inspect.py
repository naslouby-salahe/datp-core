"""Read-only inspection CLI adapter."""

import typer

from datp_core.pipeline.planning import PlanDisposition, expand_experiment_plan

app = typer.Typer(no_args_is_help=True)


@app.command("plan")
def inspect_plan() -> None:
    plan = expand_experiment_plan()
    for disposition in PlanDisposition:
        count = sum(entry.disposition is disposition for entry in plan.entries)
        typer.echo(f"{disposition.value}={count}")
