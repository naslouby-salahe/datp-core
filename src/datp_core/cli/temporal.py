"""Temporal evidence commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import declared_bounded_evidence_seed
from datp_core.pipeline.workflows.temporal import run_temporal_campaign, run_temporal_seed

app = typer.Typer()


@app.command("temporal-evidence-seed")
def temporal_evidence_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_bounded_evidence_seed(partition_seed)
    result = run_temporal_seed(seed)
    for analysis in result.analyses:
        recovery_ratio = analysis.recovery.recovery_ratio
        ratio = "undefined" if recovery_ratio is None else str(recovery_ratio.value)
        typer.echo(
            f"seed={seed.value} method={analysis.method.value} "
            f"drift_excess={analysis.recovery.drift_excess.value} "
            f"recovered_amount={analysis.recovery.recovered_amount.value} "
            f"recovery_ratio={ratio}"
        )


@app.command("temporal-evidence-campaign")
def temporal_evidence_campaign() -> None:
    result = run_temporal_campaign()
    methods = tuple(item.method for item in result.seeds[0].analyses) if result.seeds else ()
    typer.echo(f"seeds={len(result.seeds)} methods={','.join(method.value for method in methods)}")
