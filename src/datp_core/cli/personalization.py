"""Personalized-model and FedProx stress-test commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import declared_confirmatory_seed
from datp_core.domain.enums import ExperimentId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.ratios import DittoRegularization, ProximalCoefficient
from datp_core.pipeline.workflows.confirmatory import load_fedavg_cv_fpr_effect
from datp_core.pipeline.workflows.personalization import (
    analyze_ditto_absorption,
    analyze_fedprox_absorption,
    build_fedprox_absorption_observation,
    run_ditto_stress_test_seed,
    run_fedprox_coefficient_campaign,
    run_fedprox_grid_campaign,
    run_fedprox_stress_test_seed,
)
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import (
    DITTO_PRIMARY_REGULARIZATION,
    DITTO_TRAINING_PROTOCOLS,
    FEDPROX_COEFFICIENTS,
)
from datp_core.runtime.configuration import OUTPUTS_ROOT

app = typer.Typer(no_args_is_help=True)
_DECLARED_REGULARIZATIONS = frozenset(protocol.regularization.value for protocol in DITTO_TRAINING_PROTOCOLS)
_DECLARED_FEDPROX = frozenset(item.value for item in FEDPROX_COEFFICIENTS)


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


@app.command("ditto-stress-test-campaign")
def ditto_stress_test_campaign(
    regularization: Annotated[float, typer.Option()] = DITTO_PRIMARY_REGULARIZATION.value,
) -> None:
    if regularization not in _DECLARED_REGULARIZATIONS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_REGULARIZATIONS))
        raise typer.BadParameter(f"regularization must be one of the declared Ditto values: {allowed}")
    results = tuple(
        run_ditto_stress_test_seed(
            training_seed=seed,
            regularization=DittoRegularization(regularization),
        )
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    typer.echo(f"seeds={len(results)} regularization={regularization}")


@app.command("analyze-ditto-absorption")
def analyze_ditto_absorption_command(
    regularization: Annotated[float, typer.Option()] = DITTO_PRIMARY_REGULARIZATION.value,
) -> None:
    """Analyze Ditto absorption using per-seed FedAvg CV(FPR) corner evidence from confirmatory artifacts."""
    if regularization not in _DECLARED_REGULARIZATIONS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_REGULARIZATIONS))
        raise typer.BadParameter(f"regularization must be one of the declared Ditto values: {allowed}")
    results = tuple(
        run_ditto_stress_test_seed(
            training_seed=seed,
            regularization=DittoRegularization(regularization),
        )
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    reference_evidence = tuple(
        load_fedavg_cv_fpr_effect(
            result.personalized_coordinate.training_seed,
            experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
        for result in results
    )
    output = OUTPUTS_ROOT / "ditto_stress_test" / "nbaiot_natural_devices" / "analysis" / str(regularization)
    cohort = analyze_ditto_absorption(
        results,
        reference_evidence=reference_evidence,
        output_directory=output,
    )
    typer.echo(f"decision={cohort.decision.decision.value} seeds={len(cohort.observations)} path={output}")


@app.command("fedprox-stress-test-seed")
def fedprox_stress_test_seed(
    training_seed: Annotated[int, typer.Option(min=0)],
    coefficient: Annotated[float, typer.Option()],
) -> None:
    seed = declared_confirmatory_seed(training_seed)
    if coefficient not in _DECLARED_FEDPROX:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_FEDPROX))
        raise typer.BadParameter(f"coefficient must be one of the declared FedProx values: {allowed}")
    result = run_fedprox_stress_test_seed(
        training_seed=seed,
        coefficient=ProximalCoefficient(coefficient),
    )
    methods = ",".join(method.value for method in result.completed_threshold_methods)
    typer.echo(f"seed={seed.value} coefficient={coefficient} methods={methods} campaign={result.campaign_digest.value}")


@app.command("fedprox-coefficient-campaign")
def fedprox_coefficient_campaign(
    coefficient: Annotated[float, typer.Option()],
) -> None:
    if coefficient not in _DECLARED_FEDPROX:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_FEDPROX))
        raise typer.BadParameter(f"coefficient must be one of the declared FedProx values: {allowed}")
    results = run_fedprox_coefficient_campaign(coefficient=ProximalCoefficient(coefficient))
    typer.echo(f"seeds={len(results)} coefficient={coefficient}")


@app.command("fedprox-grid-campaign")
def fedprox_grid_campaign() -> None:
    results = run_fedprox_grid_campaign()
    typer.echo(f"runs={len(results)} coefficients={len(FEDPROX_COEFFICIENTS)}")


@app.command("analyze-fedprox-absorption")
def analyze_fedprox_absorption_command(
    coefficient: Annotated[float, typer.Option()],
) -> None:
    """Analyze FedProx absorption from paired per-seed FedAvg vs FedProx four-corner evaluation artifacts.

    Requires completed confirmatory FedAvg evaluations and FedProx evaluations under the standard
    experiment output layout for every confirmatory seed. Does not clone scalars across seeds.
    """
    if coefficient not in _DECLARED_FEDPROX:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_FEDPROX))
        raise typer.BadParameter(f"coefficient must be one of the declared FedProx values: {allowed}")
    proximal = ProximalCoefficient(coefficient)
    experiment = ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST
    try:
        observations = tuple(
            build_fedprox_absorption_observation(
                training_seed=seed,
                coefficient=proximal,
                reference=load_fedavg_cv_fpr_effect(seed, experiment=experiment),
            )
            for seed in CONFIRMATORY_SEED_COHORT.values
        )
    except ScientificContractError as error:
        raise typer.BadParameter(str(error)) from error
    output = OUTPUTS_ROOT / "fedprox_stress_test" / "nbaiot_natural_devices" / "analysis" / str(coefficient)
    cohort = analyze_fedprox_absorption(observations, output_directory=output)
    typer.echo(
        f"decision={cohort.decision.decision.value} coefficient={coefficient} "
        f"seeds={len(cohort.observations)} path={output}"
    )
