"""Typer CLI application routing commands to explicit application use cases."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import DatasetId, ExperimentId
from datp_core.interfaces.cli.formatters import print_catalogue_summary, print_planning_dag

app = typer.Typer(name="datp-core", help="DATP-Core Scientific CLI Application")
config_app = typer.Typer(help="Configuration commands")
catalogue_app = typer.Typer(help="Catalogue commands")
dataset_app = typer.Typer(help="Dataset commands")
experiment_app = typer.Typer(help="Experiment execution and planning commands")
artifact_app = typer.Typer(help="Artifact management commands")
results_app = typer.Typer(help="Result audit commands")

app.add_typer(config_app, name="config")
app.add_typer(catalogue_app, name="catalogue")
app.add_typer(dataset_app, name="dataset")
app.add_typer(experiment_app, name="experiment")
app.add_typer(artifact_app, name="artifact")
app.add_typer(results_app, name="results")

console = Console()


@config_app.command("validate")
def config_validate() -> None:
    """Validate all YAML configuration documents against schema rules."""
    application = build_application()
    application.validate_configuration.execute()
    console.print("[bold green]All configuration documents strictly validated successfully![/bold green]")


@config_app.command("explain-drift")
def config_explain_drift(current: Path, expected: Path) -> None:
    """Explain structural drift between two YAML configuration files."""
    application = build_application()
    drift = application.explain_configuration_drift.execute(current, expected)
    console.print_json(data=drift)


@catalogue_app.command("describe")
def catalogue_describe() -> None:
    """Describe resolved scientific catalogue records."""
    application = build_application()
    resolved = application.describe_catalogue.execute()
    print_catalogue_summary(resolved)


@dataset_app.command("audit")
def dataset_audit(dataset_id: str = typer.Argument(..., help="Dataset ID (e.g. nbaiot)")) -> None:
    """Audit dataset layout and source file availability."""
    application = build_application()
    report = application.audit_dataset.execute(DatasetId(dataset_id))
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


@experiment_app.command("resume")
def experiment_resume(experiment: str = typer.Option(..., "--config", "-c", help="Experiment name slug")) -> None:
    """Resume execution of a partially completed experiment."""
    application = build_application()
    report = application.resume_experiment.execute(ExperimentId(experiment))
    console.print(f"[bold green]Resumed Experiment {experiment}:[/bold green] Run ID={report.run_id.value}")


@results_app.command("audit")
def results_audit() -> None:
    """Audit result parquet artifacts using DuckDB."""
    application = build_application()
    res = application.audit_results.execute()
    console.print(res)


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
