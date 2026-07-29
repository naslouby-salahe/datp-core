"""Command-line entry points for reproducible DATP-Core operations."""

import typer

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.catalogue import DatasetPublication, dataset_binding
from datp_core.domain.enums import (
    ControlledPartitionKind,
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    ReusableDataCoordinateKind,
    SplitProtocolId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import DirichletConcentration, Seed
from datp_core.orchestration.stages.preprocess_centralized_reference import (
    PreprocessCentralizedPopulationRequest,
    preprocess_centralized_reference_population_stage,
)
from datp_core.orchestration.stages.preprocess_federated import (
    PreprocessFederatedRequest,
    preprocess_federated_stage,
)
from datp_core.populations.models import (
    ControlledPartitionCondition,
    dirichlet_condition,
    iid_condition,
)
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.runtime import DATA_ROOT

app = typer.Typer(no_args_is_help=True)

_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
_FEDERATED_PREPROCESSING_IDENTITIES = frozenset(
    {
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    }
)


@app.callback()
def command_group() -> None:
    """Reproducible DATP-Core operations."""


@app.command("materialize-canonical-datasets")
def materialize_canonical_datasets() -> None:
    """Publish or reuse every audited dataset under the fixed data root."""
    for dataset in DatasetId:
        result = materialize_canonical_dataset(dataset)
        typer.echo(
            f"{result.dataset.value} {result.publication_status.value} "
            f"rows={result.row_count} assets={len(result.assets)}"
        )


@app.command("preprocess-federated")
def preprocess_federated(
    population: PopulationId = typer.Option(..., help="Locked population identity."),
    partition_seed: int = typer.Option(..., help="Non-negative partition seed value."),
    split_protocol: SplitProtocolId = typer.Option(..., help="Locked split protocol identity."),
    preprocessing_identity: PreprocessingProtocolId = typer.Option(
        ...,
        help="Federated preprocessing identity.",
    ),
    partition_kind: ControlledPartitionKind | None = typer.Option(
        None,
        help="Required for controlled populations.",
    ),
    concentration: float | None = typer.Option(
        None,
        help="Dirichlet concentration from the declared grid when partition-kind is dirichlet.",
    ),
) -> None:
    """Construct partitions and publish federated processed assets under data/processed."""
    if preprocessing_identity not in _FEDERATED_PREPROCESSING_IDENTITIES:
        allowed = ", ".join(sorted(identity.value for identity in _FEDERATED_PREPROCESSING_IDENTITIES))
        raise typer.BadParameter(
            f"preprocessing-identity must be one of: {allowed}",
            param_hint="--preprocessing-identity",
        )
    condition = _controlled_partition_condition(partition_kind, concentration)
    result = preprocess_federated_stage(
        PreprocessFederatedRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
            dirichlet_condition=condition,
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"{result.stage.value} population={result.population.value} dataset={result.dataset.value} "
        f"seed={result.partition_seed.value} split={result.split_protocol.value} "
        f"preprocessing={result.preprocessing_identity.value} "
        f"clients={len(result.client_publications)} "
        f"published={result.published_count} reused={result.reused_count}"
    )
    for publication in result.client_publications:
        typer.echo(
            f"  {publication.client_identity.value} {publication.publication_status.value} "
            f"train={publication.train_row_count} "
            f"calibration={publication.calibration_row_count} "
            f"evaluation={publication.evaluation_row_count}"
        )


@app.command("preprocess-centralized-reference")
def preprocess_centralized_reference(
    population: PopulationId = typer.Option(..., help="Locked population identity."),
    partition_seed: int = typer.Option(..., help="Non-negative partition seed value."),
    split_protocol: SplitProtocolId = typer.Option(..., help="Locked split protocol identity."),
    partition_kind: ControlledPartitionKind | None = typer.Option(
        None,
        help="Required for controlled populations.",
    ),
    concentration: float | None = typer.Option(
        None,
        help="Dirichlet concentration from the declared grid when partition-kind is dirichlet.",
    ),
) -> None:
    """Construct partitions and publish centralized-reference processed assets under data/processed."""
    condition = _controlled_partition_condition(partition_kind, concentration)
    result = preprocess_centralized_reference_population_stage(
        PreprocessCentralizedPopulationRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=condition,
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"{result.stage.value} population={result.population.value} dataset={result.dataset.value} "
        f"seed={result.partition_seed.value} "
        f"preprocessing={result.preprocessing_identity.value} "
        f"status={result.publication_status.value} "
        f"train={result.result.train_path} "
        f"calibration={result.result.calibration_path} "
        f"evaluation={result.result.evaluation_path}"
    )


def main() -> None:
    app()


def materialize_canonical_dataset(dataset: DatasetId) -> DatasetPublication:
    canonical_root = DATA_ROOT / ReusableDataCoordinateKind.CANONICAL
    return dataset_binding(dataset).publish(raw_dataset_root(dataset), canonical_root)


def _controlled_partition_condition(
    partition_kind: ControlledPartitionKind | None,
    concentration: float | None,
) -> ControlledPartitionCondition | None:
    if partition_kind is None:
        if concentration is not None:
            raise typer.BadParameter(
                f"concentration requires --partition-kind {ControlledPartitionKind.DIRICHLET.value}",
                param_hint="--concentration",
            )
        return None
    match partition_kind:
        case ControlledPartitionKind.IID:
            if concentration is not None:
                raise typer.BadParameter(
                    "IID construction must not carry a concentration",
                    param_hint="--concentration",
                )
            return iid_condition()
        case ControlledPartitionKind.DIRICHLET:
            if concentration is None:
                raise typer.BadParameter(
                    f"--partition-kind {ControlledPartitionKind.DIRICHLET.value} requires --concentration",
                    param_hint="--concentration",
                )
            if concentration not in _DECLARED_DIRICHLET_VALUES:
                allowed = ", ".join(str(value) for value in sorted(_DECLARED_DIRICHLET_VALUES))
                raise typer.BadParameter(
                    f"concentration must be one of the declared Dirichlet grid values: {allowed}",
                    param_hint="--concentration",
                )
            try:
                return dirichlet_condition(DirichletConcentration(concentration))
            except ValueError as error:
                raise typer.BadParameter(str(error), param_hint="--concentration") from error
    raise ScientificContractError(
        "unsupported controlled partition kind",
        subject=partition_kind,
    )


if __name__ == "__main__":
    main()
