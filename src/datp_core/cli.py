"""Command-line entry points for reproducible DATP-Core operations."""

from dataclasses import dataclass
from enum import StrEnum

import typer

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.datasets.ciciot2023.schema import CICIoT2023ArtifactName
from datp_core.datasets.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.datasets.edge_iiotset.schema import EdgeArtifactName, EdgeArtifactSuffix
from datp_core.datasets.nbaiot.materialize import NBaIoTMaterializer
from datp_core.datasets.nbaiot.schema import NBaIoTArtifactName
from datp_core.domain.enums import DatasetId, PreprocessExecutionStatus, ReusableDataCoordinateKind
from datp_core.preprocessing.models import scientific_preprocessing_method
from datp_core.protocols.models import DATA_ROOT

app = typer.Typer(no_args_is_help=True)


class DatasetCliName(StrEnum):
    NBAIOT = DatasetId.NBAIOT.value
    CICIOT2023 = DatasetId.CICIOT2023.value
    EDGE_IIOTSET = DatasetId.EDGE_IIOTSET.value


@dataclass(frozen=True, slots=True)
class PreprocessCommandResult:
    dataset: DatasetId
    status: PreprocessExecutionStatus
    detail: str


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


@app.command("preprocess-dataset")
def preprocess_dataset_command(
    dataset: DatasetCliName = typer.Argument(..., help="Dataset identity to preprocess."),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Rebuild matching processed coordinates when preprocessing is scientifically executable.",
    ),
) -> None:
    """Ensure canonical assets and run scientific preprocessing for one dataset."""
    result = preprocess_dataset(DatasetId(dataset.value), overwrite=overwrite)
    typer.echo(f"{result.dataset.value} {result.status.value} {result.detail}")
    if result.status is PreprocessExecutionStatus.BLOCKED_POPULATION_CONSTRUCTION:
        raise typer.Exit(code=3)
    if result.status is PreprocessExecutionStatus.BLOCKED_SCIENTIFIC_VALUE:
        raise typer.Exit(code=2)


@app.command("preprocess-all-datasets")
def preprocess_all_datasets_command(
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Rebuild matching processed coordinates when preprocessing is scientifically executable.",
    ),
) -> None:
    """Ensure canonical assets and run scientific preprocessing for every dataset."""
    exit_code = 0
    for dataset in DatasetId:
        result = preprocess_dataset(dataset, overwrite=overwrite)
        typer.echo(f"{result.dataset.value} {result.status.value} {result.detail}")
        if result.status is PreprocessExecutionStatus.BLOCKED_POPULATION_CONSTRUCTION:
            exit_code = max(exit_code, 3)
        elif result.status is PreprocessExecutionStatus.BLOCKED_SCIENTIFIC_VALUE:
            exit_code = max(exit_code, 2)
    if exit_code:
        raise typer.Exit(code=exit_code)


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


def preprocess_dataset(dataset: DatasetId, *, overwrite: bool) -> PreprocessCommandResult:
    """Materialize/reuse canonical data, then attempt scientific preprocessing.

    Path roots are fixed by the canonical runtime declaration. ``overwrite`` only
    controls rebuild-vs-reuse of matching processed coordinates once populations and
    splits exist; it never redirects roots.
    """
    canonical = materialize_canonical_dataset(dataset)
    method = scientific_preprocessing_method()
    detail = (
        f"scientific method {method.identity.value} resolved for {canonical.dataset.value}; "
        "population and split construction remain Phase 05 before processed publication "
        f"(overwrite={overwrite})"
    )
    return PreprocessCommandResult(
        dataset=dataset,
        status=PreprocessExecutionStatus.BLOCKED_POPULATION_CONSTRUCTION,
        detail=detail,
    )


if __name__ == "__main__":
    main()
