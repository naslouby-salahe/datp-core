"""Experiment-planning CLI adapter."""

import typer

from datp_core.pipeline.campaign import build_campaign
from datp_core.pipeline.planning import expand_experiment_plan
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
    """Resolve the deterministic plan without inventing feasibility evidence."""
    plan = expand_experiment_plan()
    campaign = build_campaign(plan)
    typer.echo(
        f"plan={plan.digest} entries={len(plan.entries)} executable={len(plan.executable)} campaign={campaign.digest}"
    )
