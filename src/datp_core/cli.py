"""Command-line entry points for reproducible DATP-Core operations."""

import typer

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.catalogue import DatasetPublication, dataset_binding
from datp_core.domain.enums import DatasetId, ReusableDataCoordinateKind
from datp_core.protocols.runtime import DATA_ROOT

app = typer.Typer(no_args_is_help=True)


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


def main() -> None:
    app()


def materialize_canonical_dataset(dataset: DatasetId) -> DatasetPublication:
    canonical_root = DATA_ROOT / ReusableDataCoordinateKind.CANONICAL
    return dataset_binding(dataset).publish(raw_dataset_root(dataset), canonical_root)


if __name__ == "__main__":
    main()
