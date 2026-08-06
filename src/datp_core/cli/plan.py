"""Experiment-planning CLI adapter."""

import typer

from datp_core.pipeline.execution.engine import plan_and_build_campaign
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH, validate_protocol_graph

app = typer.Typer(no_args_is_help=True)


@app.command("validate-protocols")
def validate_protocols() -> None:
    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)
    typer.echo(
        f"populations={len(graph.populations)} experiments={len(graph.experiments)} "
        f"suppressed={len(graph.suppressed_experiment_ids)}"
    )


@app.command("build")
def build() -> None:
    plan, campaign = plan_and_build_campaign()
    typer.echo(
        f"plan={plan.digest.value} entries={len(plan.entries)} executable={len(plan.executable)} "
        f"campaign={campaign.digest.value}"
    )
