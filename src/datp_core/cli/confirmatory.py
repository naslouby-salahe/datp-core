"""Confirmatory and centralized-reference commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import declared_confirmatory_seed
from datp_core.pipeline.workflows.centralized import run_centralized_reference_seed
from datp_core.pipeline.workflows.confirmatory import (
    analyze_confirmatory_campaign,
    run_confirmatory_campaign,
    run_confirmatory_seed,
    run_family_grouped_mechanism_campaign,
    run_family_grouped_mechanism_seed,
)

app = typer.Typer(no_args_is_help=True)


@app.command("confirmatory-seed")
def confirmatory_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_confirmatory_seed(training_seed)
    result = run_confirmatory_seed(seed)
    typer.echo(f"seed={seed.value} thresholds={','.join(item.value for item in result.completed_threshold_methods)}")


@app.command("confirmatory-campaign")
def confirmatory_campaign() -> None:
    result = run_confirmatory_campaign()
    typer.echo(f"seeds={len(result.seeds)}")


@app.command("analyze-confirmatory")
def analyze_confirmatory() -> None:
    typer.echo(str(analyze_confirmatory_campaign()))


@app.command("family-grouped-mechanism-seed")
def family_grouped_mechanism_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_confirmatory_seed(training_seed)
    result = run_family_grouped_mechanism_seed(seed)
    typer.echo(f"seed={seed.value} thresholds={','.join(item.value for item in result.completed_threshold_methods)}")


@app.command("family-grouped-mechanism-campaign")
def family_grouped_mechanism_campaign() -> None:
    result = run_family_grouped_mechanism_campaign()
    typer.echo(f"seeds={len(result.seeds)}")


@app.command("centralized-reference-seed")
def centralized_reference_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_confirmatory_seed(training_seed)
    evaluation = run_centralized_reference_seed(seed)
    typer.echo(
        f"seed={seed.value} status={evaluation.publication_status.value} "
        f"threshold={evaluation.evaluation.threshold.value}"
    )
