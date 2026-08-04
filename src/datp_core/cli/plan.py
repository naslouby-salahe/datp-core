"""Experiment-planning CLI adapter."""

import typer

from datp_core.pipeline.campaign import build_campaign
from datp_core.pipeline.planning import expand_experiment_plan

app = typer.Typer(no_args_is_help=True)


@app.command("build")
def build() -> None:
    """Resolve the deterministic plan without inventing feasibility evidence."""
    plan = expand_experiment_plan()
    campaign = build_campaign(plan)
    typer.echo(
        f"plan={plan.digest} entries={len(plan.entries)} executable={len(plan.executable)} "
        f"campaign={campaign.digest}"
    )
