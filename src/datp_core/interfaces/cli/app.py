"""Typer CLI application routing commands to explicit application use cases."""

from __future__ import annotations

from pathlib import Path

import cattrs
import typer
from rich.console import Console

from datp_core.composition.root import build_application, build_config_only_application
from datp_core.config.resolver import resolve_project_configuration
from datp_core.config.yaml_loader import ConfigurationError
from datp_core.domain.identifiers import DatasetId, ExperimentId
from datp_core.interfaces.cli.formatters import print_catalogue_summary, print_planning_dag

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
_converter = cattrs.Converter()


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
    console.print_json(data=_converter.unstructure(drift))
    if drift.has_drift:
        raise typer.Exit(code=1)


@config_app.command("explain-scientific-drift")
def config_explain_scientific_drift(
    current_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as current"),
    expected_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as expected"),
) -> None:
    """Explain structured scientific drift between two independently resolved configurations."""
    application = build_config_only_application()
    current_config = resolve_project_configuration(config_dir=current_config_dir)
    expected_config = resolve_project_configuration(config_dir=expected_config_dir)
    drift = application.explain_scientific_drift.execute(current_config=current_config, expected_config=expected_config)
    console.print_json(data=_converter.unstructure(drift))
    if drift.has_drift:
        raise typer.Exit(code=1)


@config_app.command("explain-execution-drift")
def config_explain_execution_drift(
    current_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as current"),
    expected_config_dir: Path = typer.Option(..., help="Resolved configuration directory to treat as expected"),
) -> None:
    """Explain structured execution drift between two independently resolved configurations."""
    application = build_config_only_application()
    current_config = resolve_project_configuration(config_dir=current_config_dir)
    expected_config = resolve_project_configuration(config_dir=expected_config_dir)
    drift = application.explain_execution_drift.execute(current_config=current_config, expected_config=expected_config)
    console.print_json(data=_converter.unstructure(drift))
    if drift.has_drift:
        raise typer.Exit(code=1)


@config_app.command("fingerprint")
def config_fingerprint() -> None:
    """Print the resolved scientific and execution fingerprints for the active configuration."""
    application = build_config_only_application()
    scientific, execution = application.fingerprint_config.execute(application.config)
    console.print_json(data={"scientific_fingerprint": scientific.value, "execution_fingerprint": execution.value})


@catalogue_app.command("describe")
def catalogue_describe() -> None:
    """Describe resolved scientific catalogue records."""
    application = build_config_only_application()
    resolved = application.describe_project.execute()
    print_catalogue_summary(resolved)


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
def experiment_plan(experiment: str = typer.Option(..., "--config", "-c", help="Experiment name slug")) -> None:
    """Plan pre-execution job DAG for an experiment."""
    application = build_application()
    graph = application.plan_experiment.execute(ExperimentId(experiment))
    print_planning_dag(graph, experiment)


@experiment_app.command("run")
def experiment_run(experiment: str = typer.Option(..., "--config", "-c", help="Experiment name slug")) -> None:
    """Execute experiment pipeline."""
    application = build_application()
    report = application.execute_experiment.execute(ExperimentId(experiment))
    msg = (
        f"[bold green]Executed Experiment {experiment}:[/bold green] "
        f"Run ID={report.run_id.value}, Outcomes={len(report.outcomes)}"
    )
    console.print(msg)


@results_app.command("query")
def results_query(sql: str = typer.Argument(..., help="SQL query string")) -> None:
    """Run interactive DuckDB query over Parquet result artifacts."""
    application = build_application()
    res = application.query_results.execute(sql)
    console.print(res)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
