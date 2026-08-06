"""Historical-anchor CLI adapter."""

from pathlib import Path
from typing import Annotated

import typer

from datp_core.anchor.gate import load_anchor_gate_decision
from datp_core.anchor.reproduction import historical_sources_for_seed_directories
from datp_core.domain.errors import AnchorReproductionError
from datp_core.pipeline.workflows.anchor import (
    VerifyAnchorStageRequest,
    VerifyAnchorStageResult,
    verify_anchor,
)
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL

app = typer.Typer(no_args_is_help=True)

_DEFAULT_DIAGNOSTICS = Path("outputs/anchor/diagnostics")


def _echo_gate_status(result: VerifyAnchorStageResult) -> None:
    typer.echo(f"gate={result.status.gate_status.value} readiness={result.status.dependent_readiness.value}")


@app.command("verify-historical")
def verify_historical(
    shared_root: Annotated[Path, typer.Option(help="Root directory of shared-threshold historical seed results")],
    local_root: Annotated[Path, typer.Option(help="Root directory of local-threshold historical seed results")],
    diagnostics_directory: Annotated[Path, typer.Option()] = _DEFAULT_DIAGNOSTICS,
) -> None:
    """Verify the historical five-seed anchor from shared and local artifact roots."""
    sources = historical_sources_for_seed_directories(shared_root, local_root)
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=diagnostics_directory,
            historical_sources=sources,
            request_independent_reproduction=False,
        )
    )
    _echo_gate_status(result)


@app.command("verify")
def verify(
    diagnostics_directory: Annotated[Path, typer.Option()] = _DEFAULT_DIAGNOSTICS,
    shared_root: Annotated[
        Path | None,
        typer.Option(help="Shared-threshold historical root; requires --local-root"),
    ] = None,
    local_root: Annotated[
        Path | None,
        typer.Option(help="Local-threshold historical root; requires --shared-root"),
    ] = None,
    independent: Annotated[
        bool,
        typer.Option("--independent", help="Request independent training/scoring reproduction"),
    ] = False,
) -> None:
    """Verify the historical anchor; requires sources or --independent, never empty evidence."""
    if independent and (shared_root is not None or local_root is not None):
        raise typer.BadParameter(
            "independent reproduction cannot be combined with historical sources",
            param_hint="--independent",
        )
    if independent:
        result = verify_anchor(
            VerifyAnchorStageRequest(
                protocol=ANCHOR_DECISION_PROTOCOL,
                diagnostics_directory=diagnostics_directory,
                request_independent_reproduction=True,
            )
        )
        _echo_gate_status(result)
        return
    if shared_root is None and local_root is None:
        raise typer.BadParameter(
            "provide --shared-root and --local-root for historical verification, or --independent",
            param_hint=["--shared-root", "--local-root", "--independent"],
        )
    if shared_root is None or local_root is None:
        raise typer.BadParameter(
            "both --shared-root and --local-root are required together",
            param_hint=["--shared-root", "--local-root"],
        )
    sources = historical_sources_for_seed_directories(shared_root, local_root)
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=diagnostics_directory,
            historical_sources=sources,
            request_independent_reproduction=False,
        )
    )
    _echo_gate_status(result)


@app.command("inspect-gate")
def inspect_gate(
    diagnostics_directory: Annotated[Path, typer.Option()] = _DEFAULT_DIAGNOSTICS,
) -> None:
    """Load and print persisted gate status without claim-side filtering."""
    try:
        decision = load_anchor_gate_decision(diagnostics_directory)
    except AnchorReproductionError as error:
        raise typer.Exit(code=1) from error
    blocker = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    typer.echo(
        f"gate={decision.status.value} readiness={decision.dependent_readiness.value} "
        f"discrepancies={len(decision.reproduction.discrepancies)} blocker={blocker}"
    )


@app.command("reproduce-independent")
def reproduce_independent(
    diagnostics_directory: Annotated[Path, typer.Option()] = _DEFAULT_DIAGNOSTICS,
) -> None:
    """Request independent historical re-execution (blocked until training/scoring reproduction exists)."""
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=diagnostics_directory,
            request_independent_reproduction=True,
        )
    )
    _echo_gate_status(result)
