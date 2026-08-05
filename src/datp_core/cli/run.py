"""Pipeline execution CLI adapters."""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.domain.enums import ControlledPartitionKind, DatasetId, PopulationId, PreprocessingProtocolId, SplitProtocolId
from datp_core.domain.values import DirichletConcentration, DittoRegularization, Seed
from datp_core.pipeline.centralized_reference import run_centralized_reference_seed
from datp_core.pipeline.confirmatory import (
    analyze_confirmatory_campaign,
    run_confirmatory_campaign,
    run_confirmatory_seed,
)
from datp_core.pipeline.ditto_stress import run_ditto_stress_test_seed
from datp_core.pipeline.external_evidence import run_external_validation_seed
from datp_core.pipeline.fit_preprocessing import (
    FitCentralizedPopulationPreprocessingRequest,
    FitFederatedPreprocessingRequest,
    fit_centralized_population_preprocessing,
    fit_federated_preprocessing,
)
from datp_core.pipeline.materialize_dataset import MaterializeDatasetRequest, materialize_dataset
from datp_core.pipeline.temporal_evidence import (
    run_temporal_future_pair,
    run_temporal_static_reference_seed,
)
from datp_core.populations.models import ControlledPartitionCondition, dirichlet_condition, iid_condition
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.runtime import DATA_ROOT
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS

app = typer.Typer(no_args_is_help=True)
_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
_DECLARED_CONFIRMATORY_SEEDS = frozenset(item.value for item in CONFIRMATORY_SEED_COHORT.values)
_DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS = frozenset(
    item.value for item in BOUNDED_EVIDENCE_SEED_COHORT.values
)
_FEDERATED_PREPROCESSING_IDENTITIES = frozenset(
    (
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    )
)


@app.command("materialize-datasets")
def materialize_datasets() -> None:
    result = materialize_dataset(MaterializeDatasetRequest(data_root=DATA_ROOT, datasets=tuple(DatasetId)))
    for publication in result.publications:
        typer.echo(
            f"{publication.dataset.value} {publication.publication_status.value} "
            f"rows={publication.row_count} assets={len(publication.assets)}"
        )


@app.command("preprocess-federated")
def preprocess_federated(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    preprocessing_identity: Annotated[PreprocessingProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    if preprocessing_identity not in _FEDERATED_PREPROCESSING_IDENTITIES:
        allowed = ", ".join(sorted(item.value for item in _FEDERATED_PREPROCESSING_IDENTITIES))
        raise typer.BadParameter(f"preprocessing-identity must be one of: {allowed}")
    result = fit_federated_preprocessing(
        FitFederatedPreprocessingRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
            dirichlet_condition=_controlled_partition_condition(partition_kind, concentration),
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"population={result.population.value} dataset={result.dataset.value} "
        f"published={result.published_count} reused={result.reused_count}"
    )


@app.command("preprocess-centralized")
def preprocess_centralized(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    result = fit_centralized_population_preprocessing(
        FitCentralizedPopulationPreprocessingRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=_controlled_partition_condition(partition_kind, concentration),
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"population={result.population.value} dataset={result.dataset.value} status={result.publication_status.value}"
    )


@app.command("confirmatory-seed")
def confirmatory_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_confirmatory_seed(training_seed)
    result = run_confirmatory_seed(Seed(training_seed))
    typer.echo(
        f"seed={training_seed} thresholds={','.join(item.value for item in result.completed_threshold_methods)}"
    )


@app.command("confirmatory-campaign")
def confirmatory_campaign() -> None:
    result = run_confirmatory_campaign()
    typer.echo(f"seeds={len(result.seeds)}")


@app.command("analyze-confirmatory")
def analyze_confirmatory() -> None:
    typer.echo(str(analyze_confirmatory_campaign()))


@app.command("centralized-reference-seed")
def centralized_reference_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_confirmatory_seed(training_seed)
    evaluation = run_centralized_reference_seed(Seed(training_seed))
    typer.echo(
        f"seed={training_seed} status={evaluation.publication_status.value} "
        f"threshold={evaluation.evaluation.threshold.value}"
    )


@app.command("ditto-stress-test-seed")
def ditto_stress_test_seed(
    training_seed: Annotated[int, typer.Option(min=0)],
    regularization: Annotated[float, typer.Option()],
) -> None:
    _require_confirmatory_seed(training_seed)
    declared = frozenset(protocol.regularization.value for protocol in DITTO_TRAINING_PROTOCOLS)
    if regularization not in declared:
        allowed = ", ".join(str(value) for value in sorted(declared))
        raise typer.BadParameter(f"regularization must be one of the declared Ditto values: {allowed}")
    result = run_ditto_stress_test_seed(
        training_seed=Seed(training_seed),
        regularization=DittoRegularization(regularization),
    )
    typer.echo(
        f"seed={training_seed} regularization={regularization} "
        f"shared_threshold={result.shared_threshold.shared_threshold.value} "
        f"clients={len(result.shared_threshold_metrics)}"
    )


@app.command("external-validation-seed")
def external_validation_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    result = run_external_validation_seed(Seed(partition_seed))
    typer.echo(
        f"seed={partition_seed} thresholds="
        f"{','.join(item.value for item in result.completed_threshold_methods)}"
    )


@app.command("temporal-static-reference-seed")
def temporal_static_reference_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    result = run_temporal_static_reference_seed(Seed(partition_seed))
    typer.echo(
        f"seed={partition_seed} temporal_state={result.state.value} "
        f"thresholds={','.join(item.value for item in result.completed_threshold_methods)}"
    )


@app.command("temporal-future-pair-seed")
def temporal_future_pair_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    result = run_temporal_future_pair(Seed(partition_seed))
    for state_result in (result.frozen_future, result.recalibrated_future):
        thresholds = ",".join(item.value for item in state_result.completed_threshold_methods)
        typer.echo(f"seed={partition_seed} temporal_state={state_result.state.value} thresholds={thresholds}")


def _require_confirmatory_seed(training_seed: int) -> None:
    if training_seed not in _DECLARED_CONFIRMATORY_SEEDS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_CONFIRMATORY_SEEDS))
        raise typer.BadParameter(f"training-seed must be one of the declared confirmatory seeds: {allowed}")


def _require_declared_bounded_evidence_seed(partition_seed: int) -> None:
    if partition_seed not in _DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS))
        raise typer.BadParameter(f"partition-seed must be one of the declared bounded-evidence seeds: {allowed}")


def _controlled_partition_condition(
    partition_kind: ControlledPartitionKind | None,
    concentration: float | None,
) -> ControlledPartitionCondition | None:
    if partition_kind is None:
        if concentration is not None:
            raise typer.BadParameter("concentration requires --partition-kind dirichlet")
        return None
    if partition_kind is ControlledPartitionKind.IID:
        if concentration is not None:
            raise typer.BadParameter("IID construction must not carry a concentration")
        return iid_condition()
    if concentration is None:
        raise typer.BadParameter("Dirichlet construction requires --concentration")
    if concentration not in _DECLARED_DIRICHLET_VALUES:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_DIRICHLET_VALUES))
        raise typer.BadParameter(f"concentration must be one of the declared Dirichlet grid values: {allowed}")
    return dirichlet_condition(DirichletConcentration(concentration))
