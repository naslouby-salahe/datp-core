"""Temporal evidence commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import declared_bounded_evidence_seed
from datp_core.pipeline.workflows.temporal import run_temporal_campaign, run_temporal_seed

app = typer.Typer(no_args_is_help=True)


@app.command("temporal-evidence-seed")
def temporal_evidence_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_bounded_evidence_seed(partition_seed)
    result = run_temporal_seed(seed)
    for recovery in result.recoveries:
        recovery_ratio = recovery.recovery.recovery_ratio
        ratio = "undefined" if recovery_ratio is None else str(recovery_ratio.value)
        typer.echo(
            f"seed={seed.value} method={recovery.method.value} "
            f"drift_excess={recovery.recovery.drift_excess.value} "
            f"recovered_amount={recovery.recovery.recovered_amount.value} "
            f"recovery_ratio={ratio}"
        )


@app.command("temporal-evidence-campaign")
def temporal_evidence_campaign() -> None:
    result = run_temporal_campaign()
    methods = tuple(item.method for item in result.seeds[0].recoveries) if result.seeds else ()
    typer.echo(
        f"seeds={len(result.seeds)} methods={','.join(method.value for method in methods)} "
        f"analyses={len(result.analyses)}"
    )


@app.command("analyze-temporal-campaign")
def analyze_temporal_campaign_command() -> None:
    """Analyze completed temporal seeds without re-running seed execution when campaign reuses outputs.

    Seed execution remains deterministic and reuse-aware; analysis enforces the complete declared cohort.
    """
    campaign = run_temporal_campaign()
    for analysis in campaign.analyses:
        typer.echo(f"method={analysis.method.value} path={analysis.output_directory}")
