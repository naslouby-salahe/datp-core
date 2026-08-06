"""External-validation and applicability-boundary commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import declared_bounded_evidence_seed
from datp_core.pipeline.workflows.external import run_ciciot_boundary_seed, run_external_validation_seed

app = typer.Typer()


@app.command("edge-benign-equity-seed")
def edge_benign_equity_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_bounded_evidence_seed(partition_seed)
    result = run_external_validation_seed(seed)
    typer.echo(
        f"seed={seed.value} population={result.population.value} thresholds="
        f"{','.join(item.value for item in result.completed_threshold_methods)}"
    )


@app.command("ciciot-file-client-boundary-seed")
def ciciot_file_client_boundary_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    seed = declared_bounded_evidence_seed(partition_seed)
    result = run_ciciot_boundary_seed(seed)
    typer.echo(
        f"seed={seed.value} population={result.population.value} thresholds="
        f"{','.join(item.value for item in result.completed_threshold_methods)}"
    )
