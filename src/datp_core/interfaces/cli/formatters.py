"""Rich visual renderers for CLI commands."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.planning.graph import PlanningGraph

console = Console()


def print_catalogue_summary(catalogue: ResolvedProjectConfiguration) -> None:
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


def print_planning_dag(graph: PlanningGraph, experiment_name: str) -> None:
    tree = Tree(f"[bold gold1]Execution Plan DAG for Experiment: {experiment_name}[/bold gold1]")
    top_order = graph.lexicographical_topological_sort()
    for job in top_order:
        deps = ", ".join([d.value for d in job.dependencies]) or "None"
        line = (
            f"[green]{job.job_id.value}[/green] [dim]({job.stage.value})[/dim] "
            f"-> Output: [cyan]{job.output}[/cyan] (Deps: {deps})"
        )
        tree.add(line)
    console.print(tree)
