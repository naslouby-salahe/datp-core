"""Dataset materialization and preprocessing commands."""

from typing import Annotated

import typer

from datp_core.cli.validation import controlled_partition_condition, require_federated_preprocessing
from datp_core.datasets.service import DatasetMaterializationRequest, materialize_datasets
from datp_core.domain.enums import (
    ControlledPartitionKind,
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.domain.values import Seed
from datp_core.preprocessing.centralized import CentralizedPopulationPreprocessingRequest, preprocess_centralized_population
from datp_core.preprocessing.service import FederatedPreprocessingRequest, preprocess_federated
from datp_core.runtime.configuration import DATA_ROOT

app = typer.Typer()


@app.command("materialize-datasets")
def materialize_all_datasets() -> None:
    result = materialize_datasets(DatasetMaterializationRequest(data_root=DATA_ROOT, datasets=tuple(DatasetId)))
    for publication in result.publications:
        typer.echo(
            f"{publication.dataset.value} {publication.publication_status.value} "
            f"rows={publication.row_count} assets={len(publication.assets)}"
        )


@app.command("preprocess-federated")
def preprocess_federated_command(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    preprocessing_identity: Annotated[PreprocessingProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    identity = require_federated_preprocessing(preprocessing_identity)
    result = preprocess_federated(
        FederatedPreprocessingRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            preprocessing_identity=identity,
            data_root=DATA_ROOT,
            dirichlet_condition=controlled_partition_condition(partition_kind, concentration),
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"population={result.population.value} dataset={result.dataset.value} "
        f"published={result.published_count} reused={result.reused_count}"
    )


@app.command("preprocess-centralized")
def preprocess_centralized_command(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    result = preprocess_centralized_population(
        CentralizedPopulationPreprocessingRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=controlled_partition_condition(partition_kind, concentration),
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"population={result.population.value} dataset={result.dataset.value} "
        f"status={result.publication_status.value}"
    )
