"""Typer CLI application routing commands to explicit application use cases.

Argument parsing and presentation only, never concrete infrastructure directly -- everything
goes through ``app.py``.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from datp_core.app import ConfigurationError, build_application, build_config_only_application
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import DatasetId, ExperimentId
from datp_core.experiments.execution.runner import ExperimentRunStatus

app = typer.Typer(name="datp-core", help="DATP-Core Scientific CLI Application")
config_app = typer.Typer(help="Configuration commands")
catalogue_app = typer.Typer(help="Catalogue commands")
dataset_app = typer.Typer(help="Dataset commands")
experiment_app = typer.Typer(help="Experiment execution and planning commands")
results_app = typer.Typer(help="Result audit commands")

app.add_typer(config_app, name="config")
app.add_typer(catalogue_app, name="catalogue")
app.add_typer(dataset_app, name="dataset")
app.add_typer(experiment_app, name="experiment")
app.add_typer(results_app, name="results")

console = Console()

_EXPERIMENT_SLUG_HELP = "Experiment name slug"


def _print_catalogue_summary(catalogue: ResolvedProjectConfiguration) -> None:
    table = Table(title="DATP-Core Catalogue Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Study Populations", str(len(catalogue.populations)))
    table.add_row("Registered Experiments", str(len(catalogue.experiments)))
    table.add_row("Training Profiles", str(len(catalogue.training_profiles)))
    table.add_row("Checkpoint Profiles", str(len(catalogue.checkpoint_profiles)))
    table.add_row("Seed Cohorts", str(len(catalogue.seed_cohorts)))

    console.print(table)
    console.print(f"[bold blue]Scientific Fingerprint:[/bold blue] {catalogue.scientific_fingerprint.value}")


def _print_planning_dag(graph, experiment_name: str) -> None:
    from datp_core.pipeline.graph.traversal import lexicographical_topological_sort

    tree = Tree(f"[bold gold1]Execution Plan DAG for Experiment: {experiment_name}[/bold gold1]")
    top_order = lexicographical_topological_sort(graph)
    for job in top_order:
        deps = ", ".join([d.label for d in job.dependencies]) or "None"
        outputs = ", ".join(output.relative_path for output in job.outputs)
        line = (
            f"[green]{job.node_key.label}[/green] [dim]({job.stage.value})[/dim] "
            f"-> Output: [cyan]{outputs}[/cyan] (Deps: {deps})"
        )
        tree.add(line)
    console.print(tree)


@config_app.command("validate")
def config_validate() -> None:
    """Validate all YAML configuration documents against schema and cross-reference rules."""
    try:
        application = build_config_only_application()
    except ConfigurationError as exc:
        console.print("[bold red]Configuration validation failed:[/bold red]")
        console.print(f"  [red]-[/red] {exc}")
        raise typer.Exit(code=1) from exc
    report = application.validate_configuration.execute()
    for warning in report.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    if not report.is_valid:
        console.print("[bold red]Configuration validation failed:[/bold red]")
        for error in report.errors:
            console.print(f"  [red]-[/red] {error}")
        raise typer.Exit(code=1)
    console.print("[bold green]All configuration documents strictly validated successfully![/bold green]")


@config_app.command("explain-drift")
def config_explain_drift(current: Path, expected: Path) -> None:
    """Explain structural drift between two authored YAML configuration files."""
    application = build_config_only_application()
    drift = application.explain_authored_drift.execute(current, expected)
    console.print_json(data=drift.model_dump(mode="json"))
    if drift.has_drift:
        raise typer.Exit(code=1)


@config_app.command("explain-scientific-drift")
def config_explain_scientific_drift(
    current_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as current"),
    expected_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as expected"),
) -> None:
    """Explain structured scientific drift between two independently resolved configurations."""
    application = build_config_only_application()
    drift = application.explain_scientific_drift_between_dirs(current_config_dir, expected_config_dir)
    console.print_json(data=drift.model_dump(mode="json"))
    if drift.has_drift:
        raise typer.Exit(code=1)


@config_app.command("explain-execution-drift")
def config_explain_execution_drift(
    current_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as current"),
    expected_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as expected"),
) -> None:
    """Explain structured execution drift between two independently resolved configurations."""
    application = build_config_only_application()
    drift = application.explain_execution_drift_between_dirs(current_config_dir, expected_config_dir)
    console.print_json(data=drift.model_dump(mode="json"))
    if drift.has_drift:
        raise typer.Exit(code=1)


@config_app.command("fingerprint")
def config_fingerprint() -> None:
    """Print the resolved scientific and execution fingerprints for the active configuration."""
    application = build_config_only_application()
    scientific, execution = application.fingerprint_config.execute(application.config)
    console.print_json(
        data={
            "scientific_fingerprint": scientific.value,
            "execution_fingerprint": execution.value,
        }
    )


@catalogue_app.command("describe")
def catalogue_describe() -> None:
    """Describe resolved scientific catalogue records."""
    application = build_config_only_application()
    resolved = application.describe_project.execute()
    _print_catalogue_summary(resolved)


@dataset_app.command("audit")
def dataset_audit(dataset_id: str = typer.Argument(..., help="Dataset ID (e.g. nbaiot)")) -> None:
    """Audit dataset layout and source file availability."""
    application = build_application()
    try:
        dataset = application.config.datasets[DatasetId(dataset_id)]
    except KeyError as exc:
        raise typer.BadParameter(f"Unknown configured dataset: {dataset_id}") from exc
    report = application.audit_dataset.execute(dataset)
    msg = (
        f"[bold green]Dataset Audit for {dataset_id}:[/bold green] "
        f"Found={report.raw_source_found}, Files={report.file_count}"
    )
    console.print(msg)


@experiment_app.command("plan")
def experiment_plan(
    experiment: str = typer.Option(..., "--config", "-c", help=_EXPERIMENT_SLUG_HELP),
) -> None:
    """Plan pre-execution job DAG for an experiment."""
    application = build_application()
    experiment_id = ExperimentId(experiment)
    graph = application.build_experiment_plan(experiment_id)
    _print_planning_dag(graph, experiment)


@experiment_app.command("run")
def experiment_run(
    experiment: str = typer.Option(..., "--config", "-c", help=_EXPERIMENT_SLUG_HELP),
    override: bool = typer.Option(False, "--override", help="Delete existing experiment output and run from scratch"),
) -> None:
    """Execute a single experiment pipeline.

    When a valid completed output exists, the experiment is skipped (SKIPPED_EXISTING).
    When an incomplete or failed output exists, --override is required to delete and restart.
    """
    application = build_application()
    experiment_id = ExperimentId(experiment)
    result = application.run_experiment.run(experiment_id, override=override)
    if result.status is ExperimentRunStatus.SKIPPED_EXISTING:
        console.print(f"[blue]SKIPPED_EXISTING: experiment {experiment} already has a valid completed output.[/blue]")
        console.print("[dim]Use --override to delete it and run the experiment again from scratch.[/dim]")
        return
    if not result.success:
        console.print(f"[red]Experiment {experiment} was not run: {result.error_message}[/red]")
        raise typer.Exit(code=1)
    report = result.report
    if report is None:
        console.print(f"[red]Experiment {experiment} completed without an execution report.[/red]")
        raise typer.Exit(code=1)
    msg = (
        f"[bold green]Executed Experiment {experiment}:[/bold green] "
        f"Outcomes={len(report.outcomes)}, "
        f"Success={report.successful_jobs}, Failed={report.failed_jobs}"
    )
    console.print(msg)

    if report.failed_jobs > 0:
        raise typer.Exit(code=1)


campaign_app = typer.Typer(help="Campaign orchestration commands")
app.add_typer(campaign_app, name="campaign")


@campaign_app.command("run")
def campaign_run(
    override_all: bool = typer.Option(
        False,
        "--override-all",
        help="Delete all campaign-managed experiment outputs and run from scratch",
    ),
) -> None:
    """Execute the full scientific campaign in canonical dependency order."""
    application = build_application()
    report = application.run_campaign.run(override_all=override_all)

    table = Table(title="Campaign Execution Summary")
    table.add_column("Experiment", style="cyan")
    table.add_column("Status", style="green")

    for result in report.results:
        status_style = {
            "skipped_existing": "blue",
            "incomplete_restarted": "yellow",
            "executed": "green",
            "blocked_prerequisite": "red",
            "blocked_anchor": "red",
            "incompatible": "red",
            "failed": "red",
        }.get(result.status.value, "white")
        table.add_row(
            result.experiment_id.value,
            f"[{status_style}]{result.status.value}[/{status_style}]",
        )

    console.print(table)
    console.print(
        f"[bold]Total: {report.total_experiments}[/bold] | "
        f"[green]Completed/Skipped: {report.completed_or_skipped}[/green] | "
        f"[yellow]Executed: {report.executed}[/yellow] | "
        f"[red]Blocked: {report.blocked}[/red] | "
        f"[red]Failed: {report.failed}[/red]"
    )

    if not report.success:
        console.print("[bold red]Campaign completed with failures.[/bold red]")
        raise typer.Exit(code=1)
    console.print("[bold green]Campaign completed successfully![/bold green]")


@results_app.command("query")
def results_query(sql: str = typer.Argument(..., help="SQL query string")) -> None:
    """Run interactive DuckDB query over Parquet result artifacts."""
    application = build_application()
    res = application.audit_svc.execute_query(sql)
    console.print(res)


diagnostic_app = typer.Typer(help="Production diagnostic commands (isolated outputs)")
app.add_typer(diagnostic_app, name="diagnostic")


@diagnostic_app.command("experiment")
def diagnostic_experiment(
    experiment: str = typer.Option(..., "--config", "-c", help=_EXPERIMENT_SLUG_HELP),
    seed_index: int = typer.Option(0, "--seed-index", help="Seed index (0-based)"),
    profile: str = typer.Option("smoke", "--profile", help="Execution profile"),
) -> None:
    """Diagnose one experiment through the real pipeline with one seed.

    Output is isolated under .tmp/diagnostics/ — never touches official outputs.
    """
    from datp_core.orchestration.diagnostics import ExperimentDiagnosticStatus

    application = build_application()
    result = application.run_diagnostic_experiment(experiment, seed_index=seed_index, profile=profile)
    if result.status is ExperimentDiagnosticStatus.DIAGNOSTIC_FAILED:
        console.print(f"[red]Diagnostic failed: {result.error}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Diagnostic for {experiment}: {result.status.value}[/green]")
    if result.scientific_fingerprint:
        console.print(f"[dim]Scientific fingerprint: {result.scientific_fingerprint}[/dim]")


@diagnostic_app.command("campaign")
def diagnostic_campaign(
    profile: str = typer.Option("smoke", "--profile", help="Execution profile"),
) -> None:
    """Diagnose the complete campaign through the real pipeline, one seed per experiment.

    Output is isolated under .tmp/diagnostics/ — never touches official outputs.
    """
    application = build_application()
    result = application.run_diagnostic_campaign(profile=profile)
    console.print("[bold]Campaign diagnostic:[/bold]")
    console.print(f"  Total: {result.total}")
    console.print(f"  Completed/Skipped: {result.completed_or_skipped}")
    console.print(f"  Executed: {result.executed}")
    console.print(f"  Blocked: {result.blocked}")
    console.print(f"  Failed: {result.failed}")
    if not result.success:
        console.print("[red]Campaign diagnostic completed with failures.[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Campaign diagnostic completed successfully.[/green]")


@diagnostic_app.command("dagster")
def diagnostic_dagster(
    experiment: str = typer.Option(..., "--config", "-c", help=_EXPERIMENT_SLUG_HELP),
) -> None:
    """Run one experiment through Dagster (canonical orchestrator)."""
    application = build_application()
    result = application.execute_dagster_experiment(experiment)
    if result is None:
        console.print(f"[red]No Dagster job found for experiment: {experiment}[/red]")
        raise typer.Exit(code=1)
    if result.success:
        console.print(f"[green]Dagster experiment {experiment} completed successfully.[/green]")
    else:
        console.print(f"[red]Dagster experiment {experiment} failed.[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
