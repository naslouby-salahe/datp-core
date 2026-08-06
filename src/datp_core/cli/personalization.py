"""Personalized-model and FedProx stress-test commands."""

from typing import Annotated

import typer

from datp_core.analysis.mechanisms import AbsorptionSeedObservation
from datp_core.cli.validation import declared_confirmatory_seed
from datp_core.domain.enums import ExperimentId, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.ratios import DittoRegularization, MetricValue
from datp_core.pipeline.workflows.confirmatory import load_fedavg_cv_fpr_effect
from datp_core.pipeline.workflows.personalization import (
    analyze_ditto_absorption,
    analyze_fedprox_absorption,
    run_ditto_stress_test_seed,
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
    """Analyze Ditto absorption using per-seed FedAvg CV(FPR) effects from confirmatory artifacts."""
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
    reference_pairs = tuple(
        load_fedavg_cv_fpr_effect(result.personalized_coordinate.training_seed) for result in results
    )
    reference_effects = tuple(effect for _, _, effect in reference_pairs)
    reference_shared_local = tuple((shared, local) for shared, local, _ in reference_pairs)
    output = OUTPUTS_ROOT / "ditto_stress_test" / "nbaiot_natural_devices" / "analysis" / str(regularization)
    cohort = analyze_ditto_absorption(
        results,
        reference_effects=reference_effects,
        output_directory=output,
        reference_shared_local_cvs=reference_shared_local,
    )
    typer.echo(f"decision={cohort.decision.decision.value} seeds={len(cohort.observations)} path={output}")


@app.command("analyze-fedprox-absorption")
def analyze_fedprox_absorption_command(
    coefficient: Annotated[float, typer.Option()],
) -> None:
    """Analyze FedProx absorption from paired per-seed FedAvg vs FedProx CV(FPR) evaluation artifacts.

    Requires completed confirmatory FedAvg evaluations and FedProx evaluations under the standard
    experiment output layout for every confirmatory seed. Does not clone scalars across seeds.
    """
    if coefficient not in _DECLARED_FEDPROX:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_FEDPROX))
        raise typer.BadParameter(f"coefficient must be one of the declared FedProx values: {allowed}")
    observations: list[AbsorptionSeedObservation] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        _, _, reference_effect = load_fedavg_cv_fpr_effect(seed)
        try:
            personalized_effect = _load_fedprox_cv_fpr_effect(seed, coefficient)
        except ScientificContractError as error:
            raise typer.BadParameter(str(error)) from error
        observations.append(
            AbsorptionSeedObservation(
                seed=seed,
                experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
                reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
                personalized_model=TrainingModelId.FEDPROX_AUTOENCODER,
                reference_effect=reference_effect,
                personalized_effect=personalized_effect,
            )
        )
    output = OUTPUTS_ROOT / "fedprox_stress_test" / "nbaiot_natural_devices" / "analysis" / str(coefficient)
    cohort = analyze_fedprox_absorption(tuple(observations), output_directory=output)
    typer.echo(
        f"decision={cohort.decision.decision.value} coefficient={coefficient} "
        f"seeds={len(cohort.observations)} path={output}"
    )


def _load_fedprox_cv_fpr_effect(training_seed, coefficient: float) -> MetricValue:
    """Load FedProx SHARED−LOCAL CV(FPR) when evaluation documents exist for the coefficient."""
    from datp_core.domain.enums import FederatedThresholdMethod, MetricId
    from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
    from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
    from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
    from datp_core.pipeline.planning import expand_experiment_plan
    from datp_core.pipeline.publication.layout import evaluation_run_directory
    from datp_core.protocols.experiments import EXPERIMENTS
    from datp_core.protocols.seeds import SeedCohort

    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
    )
    effects: list[MetricValue] = []
    for method in (FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD):
        matches = tuple(
            entry.coordinate
            for entry in plan.entries
            if entry.coordinate.threshold_method is method
            and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
            and entry.coordinate.model_coefficient is not None
            and abs(entry.coordinate.model_coefficient.value - coefficient) < 1e-15
        )
        if len(matches) != 1:
            raise ScientificContractError(
                f"FedProx evaluation coordinate unresolved for seed={training_seed.value} "
                f"coefficient={coefficient} method={method.value}"
            )
        path = (
            evaluation_run_directory(OUTPUTS_ROOT, matches[0])
            / EvaluationRunAssetDirectory.EVALUATION
            / FederatedEvaluationAssetName.DOCUMENT
        )
        if not path.is_file():
            raise ScientificContractError(f"missing FedProx evaluation document: {path}")
        effects.append(population_metric(load_evaluation_document(path), MetricId.FPR_COEFFICIENT_OF_VARIATION))
    return MetricValue(effects[0].value - effects[1].value)
