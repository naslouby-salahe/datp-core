"""Read-only inspection CLI adapter."""

import typer

from datp_core.domain.enums import ExperimentId, PopulationId
from datp_core.pipeline.planning import PlanDisposition, expand_experiment_plan
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.populations import POPULATIONS

app = typer.Typer(no_args_is_help=True)


@app.command("plan")
def inspect_plan() -> None:
    plan = expand_experiment_plan()
    for disposition in PlanDisposition:
        count = sum(entry.disposition is disposition for entry in plan.entries)
        typer.echo(f"{disposition.value}={count}")


@app.command("experiment")
def inspect_experiment(experiment: ExperimentId = typer.Argument(...)) -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is experiment)
    typer.echo(
        f"experiment={declaration.id.value} population={declaration.population.value} "
        f"model={declaration.training_model.value} role={declaration.role.value} "
        f"readiness={declaration.readiness.value}"
    )


@app.command("population")
def inspect_population(population: PopulationId = typer.Argument(...)) -> None:
    declaration = next(item for item in POPULATIONS if item.id is population)
    typer.echo(
        f"population={declaration.id.value} dataset={declaration.dataset.value} "
        f"clients={declaration.declared_client_count.value} temporal={declaration.supports_temporal_evidence}"
    )
