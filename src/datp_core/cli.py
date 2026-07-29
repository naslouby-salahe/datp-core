"""Command-line entry points for reproducible DATP-Core operations."""

import typer

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.datasets.ciciot2023.schema import CICIoT2023ArtifactName
from datp_core.datasets.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.datasets.edge_iiotset.schema import EdgeArtifactName, EdgeArtifactSuffix
from datp_core.datasets.nbaiot.materialize import NBaIoTMaterializer
from datp_core.datasets.nbaiot.schema import NBaIoTArtifactName
from datp_core.domain.enums import DatasetId, ReusableDataCoordinateKind
from datp_core.protocols.models import DATA_ROOT

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


def materialize_canonical_dataset(dataset: DatasetId):
    canonical_root = DATA_ROOT / ReusableDataCoordinateKind.CANONICAL
    match dataset:
        case DatasetId.NBAIOT:
            source_paths = tuple(
                path
                for path in sorted(raw_dataset_root(dataset).glob(f"**/*{NBaIoTArtifactName.CSV_SUFFIX}"))
                if path.name != NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
            )
            return NBaIoTMaterializer().materialize(source_paths, canonical_root)
        case DatasetId.CICIOT2023:
            source_paths = tuple(
                sorted(raw_dataset_root(dataset).glob(f"**/{CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY}/*.csv"))
            )
            return CICIoT2023Materializer().materialize(source_paths, canonical_root)
        case DatasetId.EDGE_IIOTSET:
            raw_root = raw_dataset_root(dataset) / EdgeArtifactName.DATASET_BUNDLE_DIRECTORY
            benign_paths = tuple(
                sorted((raw_root / EdgeArtifactName.NORMAL_TRAFFIC_DIRECTORY).glob(f"*/*{EdgeArtifactSuffix.CSV}"))
            )
            attack_paths = tuple(
                sorted(
                    (raw_root / EdgeArtifactName.ATTACK_TRAFFIC_DIRECTORY).glob(
                        f"*{EdgeArtifactName.ATTACK_FILE_SUFFIX}"
                    )
                )
            )
            return EdgeIIoTsetMaterializer().materialize(benign_paths, attack_paths, canonical_root)


if __name__ == "__main__":
    main()
