"""Thin research-facing Typer CLI for DATP-Core.

Public inputs are limited to EXPERIMENT_ID, DATASET_ID, and --overwrite.
Scientific configuration is resolved only from typed protocol declarations.
"""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.cli.anchor import app as anchor_app
from datp_core.cli.execution import app as run_app
from datp_core.cli.validation import echo_error, echo_lines, map_exception_to_exit
from datp_core.domain.enums import DatasetId, ExperimentId
from datp_core.pipeline.workflows import (
    build_programme_plan,
    format_plan,
    format_status,
    generate_report,
    preprocess_datasets,
    programme_status,
    run_smoke,
    validate_programme,
)

app = typer.Typer(
    no_args_is_help=True,
    help="DATP-Core journal-extension research interface.",
)
app.add_typer(run_app, name="run")
app.add_typer(anchor_app, name="anchor")


@app.command("validate")
def validate_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:
    """Validate the scientific programme or one experiment and its dependencies."""
    try:
        result = validate_programme(experiment_id)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    echo_lines(
        (
            f"populations={len(result.graph.populations)}",
            f"experiments={len(result.experiment_ids)}",
            f"suppressed={len(result.graph.suppressed_experiment_ids)}",
            f"registered_workflows={len(result.registered_workflows)}",
            f"unregistered_declared={len(result.unregistered_declared)}",
        )
    )


@app.command("plan")
def plan_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:
    """Display the deterministic campaign or experiment plan (dry-run)."""
    try:
        presentation = build_programme_plan(experiment_id)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(format_plan(presentation))


@app.command("preprocess")
def preprocess_command(
    dataset_id: Annotated[DatasetId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Rebuild dataset-level canonical artifacts")] = False,
) -> None:
    """Materialize canonical datasets (all declared datasets when omitted)."""
    try:
        result = preprocess_datasets(dataset_id, overwrite=overwrite)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    for publication in result.publications:
        typer.echo(publication)


@app.command("smoke")
def smoke_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Rebuild smoke artifacts only")] = False,
) -> None:
    """Smoke-test one experiment or the full programme with one canonical seed each."""
    try:
        result = run_smoke(experiment_id, overwrite=overwrite)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(f"smoke experiments={len(result.experiments)} detail={result.detail}")
    for item in result.experiments:
        typer.echo(f"{item.experiment.value} seeds={','.join(str(seed) for seed in item.seeds)}")


@app.command("report")
def report_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Regenerate report artifacts only")] = False,
) -> None:
    """Generate report packages from existing validated evidence."""
    try:
        result = generate_report(experiment_id, overwrite=overwrite)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(result.detail)
    for path in result.paths:
        typer.echo(str(path))


@app.command("status")
def status_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:
    """Show campaign or experiment status derived from validated artifacts."""
    try:
        report = programme_status(experiment_id)
    except Exception as error:
        echo_error(error)
        raise typer.Exit(code=map_exception_to_exit(error)) from error
    typer.echo(format_status(report))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
