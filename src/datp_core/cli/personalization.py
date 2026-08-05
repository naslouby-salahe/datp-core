"""Personalized-model stress-test commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import declared_confirmatory_seed
from datp_core.domain.values import DittoRegularization
from datp_core.pipeline.workflows.personalization import run_ditto_stress_test_seed
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS

app = typer.Typer()
_DECLARED_REGULARIZATIONS = frozenset(protocol.regularization.value for protocol in DITTO_TRAINING_PROTOCOLS)


@app.command("ditto-stress-test-seed")
def ditto_stress_test_seed(
    training_seed: Annotated[int, typer.Option(min=0)],
    regularization: Annotated[float, typer.Option()],
) -> None:
    seed = declared_confirmatory_seed(training_seed)
    if regularization not in _DECLARED_REGULARIZATIONS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_REGULARIZATIONS))
        raise typer.BadParameter(f"regularization must be one of the declared Ditto values: {allowed}")
    result = run_ditto_stress_test_seed(
        training_seed=seed,
        regularization=DittoRegularization(regularization),
    )
    typer.echo(
        f"seed={seed.value} regularization={regularization} "
        f"shared_threshold={result.shared_threshold.shared_threshold.value} "
        f"clients={len(result.shared_threshold_metrics)}"
    )
