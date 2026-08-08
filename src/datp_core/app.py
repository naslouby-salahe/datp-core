"""Thin research-facing Typer adapter for DATP-Core."""

from __future__ import annotations

from typing import Annotated, Never

import typer

from datp_core.domain.enums import DatasetId, ExperimentId
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
from datp_core.pipeline.programme import (
    OverwriteMode,
    ProgrammeExecutionMode,
    anchor_status,
    build_programme_plan,
    format_plan,
    format_status,
    generate_report,
    preprocess_datasets,
    programme_status,
    reproduce_anchor,
    run_campaign,
    run_experiment,
    run_smoke,
    validate_programme,
    verify_anchor_programme,
)


app = typer.Typer(no_args_is_help=True, help="DATP-Core research interface.")
run_app = typer.Typer(no_args_is_help=True, help="Run one experiment or the complete campaign.")
anchor_app = typer.Typer(no_args_is_help=True, help="Historical anchor equivalence gate.")
app.add_typer(run_app, name="run")
app.add_typer(anchor_app, name="anchor")


type CliHandledError = DatpCoreError | ValueError


def _overwrite_mode(enabled: bool) -> OverwriteMode:
    return OverwriteMode.REBUILD if enabled else OverwriteMode.KEEP_EXISTING


def _exit_code(error: CliHandledError) -> int:
    if isinstance(error, MissingPrerequisiteError):
        if error.reason == "anchor_gate":
            return CliExitCode.ANCHOR_GATE_FAILURE.value
        return CliExitCode.INCOMPLETE_PREREQUISITE.value
    if isinstance(error, UnknownIdentifierError):
        return CliExitCode.UNKNOWN_IDENTIFIER.value
    if isinstance(error, ProtocolValidationError):
        return CliExitCode.INVALID_DECLARATION.value
    if isinstance(error, ReportEvidenceError):
        return CliExitCode.MISSING_REPORT_EVIDENCE.value
    if isinstance(error, ArtifactIntegrityError):
        return CliExitCode.INVALID_ARTIFACT.value
    if isinstance(error, AnchorReproductionError):
        return CliExitCode.ANCHOR_GATE_FAILURE.value
    if isinstance(error, ScientificContractError):
        return CliExitCode.SCIENTIFIC_CONTRACT.value
    if isinstance(error, ValueError):
        return CliExitCode.USAGE.value
    return CliExitCode.INTERNAL.value


def _fail(error: CliHandledError) -> Never:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=_exit_code(error)) from error


@app.command("validate")
def validate_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:
    """Validate the complete scientific programme or one experiment."""
    try:
        result = validate_programme(experiment_id)
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(f"populations={len(result.graph.populations)}")
    typer.echo(f"experiments={len(result.experiment_ids)}")
    typer.echo(f"suppressed={len(result.suppressed_experiments)}")
    typer.echo(f"registered_recipes={len(result.registered_recipes)}")


@app.command("plan")
def plan_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:
    """Display the deterministic programme or experiment plan without execution."""
    try:
        presentation = build_programme_plan(experiment_id)
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(format_plan(presentation))


@app.command("preprocess")
def preprocess_command(
    dataset_id: Annotated[DatasetId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild dataset-level canonical artifacts"),
    ] = False,
) -> None:
    """Materialize one dataset, or every declared dataset when omitted."""
    try:
        result = preprocess_datasets(dataset_id, overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    for publication in result.publications:
        typer.echo(publication)


@app.command("smoke")
def smoke_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild smoke-owned artifacts"),
    ] = False,
) -> None:
    """Smoke-test one experiment or the programme with one canonical seed each."""
    try:
        result = run_smoke(experiment_id, overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(f"smoke experiments={len(result.experiments)} detail={result.detail}")
    if result.anchor_failure is not None:
        typer.echo(f"anchor_failure={result.anchor_failure}")
    for experiment in result.experiments:
        methods = ",".join(
            f"{outcome.method.value}={outcome.status.value}" for outcome in experiment.method_outcomes
        )
        seeds = ",".join(str(seed.value) for seed in experiment.seeds)
        typer.echo(
            f"{experiment.experiment.value} seeds={seeds} detail={experiment.detail} methods={methods}"
        )


@app.command("report")
def report_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Regenerate report-owned artifacts"),
    ] = False,
) -> None:
    """Generate report packages from existing validated evidence."""
    try:
        result = generate_report(experiment_id, overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(result.detail)
    for path in result.paths:
        typer.echo(str(path))


@app.command("status")
def status_command(
    experiment_id: Annotated[ExperimentId | None, typer.Argument(case_sensitive=False)] = None,
) -> None:
    """Show programme or experiment status derived from validated artifacts."""
    try:
        result = programme_status(experiment_id)
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(format_status(result))


@run_app.command("experiment")
def run_experiment_command(
    experiment_id: Annotated[ExperimentId, typer.Argument(case_sensitive=False)],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild this experiment's owned artifacts"),
    ] = False,
) -> None:
    """Run one experiment's complete declared recipe and seed cohort."""
    try:
        result = run_experiment(experiment_id, overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    methods = ",".join(f"{item.method.value}={item.status.value}" for item in result.method_outcomes)
    typer.echo(
        f"experiment={result.experiment.value} seeds={len(result.seeds)} "
        f"output_root={result.output_root} detail={result.detail} methods={methods}"
    )


@run_app.command("campaign")
def run_campaign_command(
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild campaign-owned execution and analysis artifacts"),
    ] = False,
) -> None:
    """Run the complete scientific programme in deterministic dependency order."""
    try:
        result = run_campaign(overwrite=_overwrite_mode(overwrite))
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(f"campaign experiments={len(result.experiments)} detail={result.detail}")


@anchor_app.command("reproduce")
def reproduce_anchor_command(
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rebuild independent anchor reproduction"),
    ] = False,
) -> None:
    """Run independent anchor reproduction for the locked historical seed cohort."""
    try:
        result = reproduce_anchor(
            overwrite=_overwrite_mode(overwrite),
            mode=ProgrammeExecutionMode.FULL,
        )
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(f"gate={result.gate_status.value} readiness={result.dependent_readiness.value} detail={result.detail}")


@anchor_app.command("verify")
def verify_anchor_command() -> None:
    """Verify reproduced anchor evidence against the locked historical reference."""
    try:
        result = verify_anchor_programme(mode=ProgrammeExecutionMode.FULL)
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(f"gate={result.gate_status.value} readiness={result.dependent_readiness.value} detail={result.detail}")


@anchor_app.command("status")
def anchor_status_command() -> None:
    """Show anchor gate and dependent readiness."""
    try:
        result = anchor_status()
    except (DatpCoreError, ValueError) as error:
        _fail(error)
    typer.echo(f"gate={result.gate_status.value} readiness={result.dependent_readiness.value} detail={result.detail}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
