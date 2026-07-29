"""Command-line entry points for reproducible DATP-Core operations."""

import typer

from datp_core.datasets.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.datasets.ciciot2023.schema import CICIoT2023ArtifactName
from datp_core.datasets.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.datasets.edge_iiotset.schema import EdgeArtifactName, EdgeArtifactSuffix
from datp_core.datasets.nbaiot.materialize import NBaIoTMaterializer
from datp_core.datasets.nbaiot.schema import NBaIoTArtifactName
from datp_core.domain.enums import DatasetId
from datp_core.protocols.models import DATA_ROOT

app = typer.Typer(no_args_is_help=True)


@app.callback()
def command_group() -> None:
    """Reproducible DATP-Core operations."""


@app.command("materialize-canonical-datasets")
def materialize_canonical_datasets() -> None:
    """Publish or reuse every audited dataset under the fixed data root."""
    for dataset in DatasetId:
        result = _materialize_dataset(dataset)
        typer.echo(
            f"{result.dataset.value} {result.publication_status.value} "
            f"rows={result.row_count} assets={len(result.assets)}"
        )


def main() -> None:
    app()


def _materialize_dataset(dataset: DatasetId):
    match dataset:
        case DatasetId.NBAIOT:
            source_paths = tuple(
                path
                for path in sorted((DATA_ROOT / "raw" / "N-BaIoT").glob(f"**/*{NBaIoTArtifactName.CSV_SUFFIX}"))
                if path.name != NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
            )
            return NBaIoTMaterializer().materialize(source_paths, DATA_ROOT / "canonical")
        case DatasetId.CICIOT2023:
            source_paths = tuple(
                sorted(
                    (DATA_ROOT / "raw" / "CIC_IOT_Dataset2023").glob(
                        f"**/{CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY}/*.csv"
                    )
                )
            )
            return CICIoT2023Materializer().materialize(source_paths, DATA_ROOT / "canonical")
        case DatasetId.EDGE_IIOTSET:
            raw_root = DATA_ROOT / "raw" / "Edge-IIoTset" / "Edge-IIoTset dataset"
            benign_paths = tuple(
                sorted((raw_root / EdgeArtifactName.NORMAL_TRAFFIC_DIRECTORY).glob(f"*/*{EdgeArtifactSuffix.CSV}"))
            )
            attack_paths = tuple(
                sorted((raw_root / EdgeArtifactName.ATTACK_TRAFFIC_DIRECTORY).glob(EdgeArtifactName.ATTACK_FILE_SUFFIX))
            )
            return EdgeIIoTsetMaterializer().materialize(benign_paths, attack_paths, DATA_ROOT / "canonical")


if __name__ == "__main__":
    main()
