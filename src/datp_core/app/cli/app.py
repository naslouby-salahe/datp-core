from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from datp_core.app.campaign import build_programme_plan, format_plan, preprocess_datasets
from datp_core.app.cli.anchor import app as anchor_app
from datp_core.app.cli.execution import app as run_app
from datp_core.app.cli.validation import fail
from datp_core.app.contracts import OverwriteMode
from datp_core.app.research import format_status, generate_report, programme_status, run_smoke
from datp_core.app.validation import validate_programme
from datp_core.artifacts.release import validate_release_bundle
from datp_core.core.errors import DatpCoreError
from datp_core.core.identifiers import DatasetId, ExperimentId

app = typer.Typer(no_args_is_help=True, help="DATP-Core journal-extension research interface.")
app.add_typer(run_app, name="run")
app.add_typer(anchor_app, name="anchor")


def _overwrite_mode(overwrite: bool) -> OverwriteMode:
    return OverwriteMode.REBUILD if overwrite else OverwriteMode.KEEP_EXISTING


@app.command("validate")
def validate_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:

    try:
        result = validate_programme(experiment_id)
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"populations={len(result.graph.populations)}")
    typer.echo(f"experiments={len(result.experiment_ids)}")
    typer.echo(f"suppressed={len(result.suppressed_experiments)}")
    typer.echo(f"registered_recipes={len(result.registered_recipes)}")


@app.command("plan")
def plan_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:

    try:
        presentation = build_programme_plan(experiment_id)
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(format_plan(presentation))


@app.command("preprocess")
def preprocess_command(
    dataset_id: Annotated[DatasetId, typer.Argument(case_sensitive=False)],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild dataset-level canonical artifacts"),
    ] = False,
) -> None:

    try:
        result = preprocess_datasets(dataset_id, overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        fail(error)
    for publication in result.publications:
        typer.echo(publication.dataset.value)


@app.command("smoke")
def smoke_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild smoke-owned artifacts"),
    ] = False,
) -> None:

    try:
        result = run_smoke(experiment_id, overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"smoke experiments={len(result.experiments)} detail={result.detail}")
    if result.anchor_failure is not None:
        typer.echo(f"anchor_failure={result.anchor_failure}")
    for item in result.experiments:
        outcomes = ",".join(f"{outcome.method.value}={outcome.status.value}" for outcome in item.method_outcomes)
        typer.echo(
            f"{item.experiment.value} seeds={','.join(str(seed.value) for seed in item.seeds)} "
            f"detail={item.detail} methods={outcomes}"
        )


@app.command("report")
def report_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:

    try:
        result = generate_report(experiment_id)
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(result.detail)
    for path in result.paths:
        typer.echo(str(path))


@app.command("status")
def status_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:

    try:
        report = programme_status(experiment_id)
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(format_status(report))


@app.command("validate-release")
def validate_release_command(
    release_root: Annotated[Path, typer.Argument()],
) -> None:
    try:
        release = validate_release_bundle(release_root)
    except (DatpCoreError, ValueError) as error:
        fail(error)
    typer.echo(f"release={release.root}")
    typer.echo(f"artifacts={len(release.entries)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
