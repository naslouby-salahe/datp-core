"""Historical-anchor CLI adapter."""

from pathlib import Path
from typing import Annotated

import typer

from datp_core.pipeline.workflows.anchor import VerifyAnchorStageRequest, verify_anchor
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL

app = typer.Typer(no_args_is_help=True)


@app.command("verify")
def verify(
    diagnostics_directory: Annotated[Path, typer.Option()] = Path("outputs/anchor/diagnostics"),
) -> None:
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=diagnostics_directory,
            observations=None,
            historical_sources=None,
            request_independent_reproduction=False,
        )
    )
    typer.echo(f"gate={result.status.gate_status.value} readiness={result.status.dependent_readiness.value}")
