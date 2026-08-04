"""Pipeline execution CLI adapters."""

from __future__ import annotations

import typer

from datp_core.domain.enums import (
    ControlledPartitionKind,
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.domain.values import DirichletConcentration, Seed
from datp_core.pipeline.campaign import (
    analyze_confirmatory_campaign,
    run_confirmatory_campaign,
    run_confirmatory_seed,
)
from datp_core.pipeline.fit_preprocessing import (
    FitCentralizedPopulationPreprocessingRequest,
    FitFederatedPreprocessingRequest,
    fit_centralized_population_preprocessing,
    fit_federated_preprocessing,
)
from datp_core.pipeline.materialize_dataset import MaterializeDatasetRequest, materialize_dataset
from datp_core.populations.models import ControlledPartitionCondition, dirichlet_condition, iid_condition
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.runtime import DATA_ROOT

app = typer.Typer(no_args_is_help=True)
_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
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
    population: PopulationId = typer.Option(...),
    partition_seed: int = typer.Option(..., min=0),
    split_protocol: SplitProtocolId = typer.Option(...),
    preprocessing_identity: PreprocessingProtocolId = typer.Option(...),
    partition_kind: ControlledPartitionKind | None = typer.Option(None),
    concentration: float | None = typer.Option(None),
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
    population: PopulationId = typer.Option(...),
    partition_seed: int = typer.Option(..., min=0),
    split_protocol: SplitProtocolId = typer.Option(...),
    partition_kind: ControlledPartitionKind | None = typer.Option(None),
    concentration: float | None = typer.Option(None),
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
        f"population={result.population.value} dataset={result.dataset.value} "
        f"status={result.publication_status.value}"
    )


@app.command("confirmatory-seed")
def confirmatory_seed(training_seed: int = typer.Option(..., min=0)) -> None:
    completed = run_confirmatory_seed(Seed(training_seed))
    typer.echo(f"seed={training_seed} thresholds={','.join(item.value for item in completed)}")


@app.command("confirmatory-campaign")
def confirmatory_campaign() -> None:
    completed = run_confirmatory_campaign()
    typer.echo(f"seeds={len(completed)}")


@app.command("analyze-confirmatory")
def analyze_confirmatory() -> None:
    typer.echo(str(analyze_confirmatory_campaign()))


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
