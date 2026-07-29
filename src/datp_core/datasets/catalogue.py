"""Authoritative typed dataset bindings and source discovery."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.datasets.capabilities import DatasetCapabilities
from datp_core.datasets.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.datasets.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.datasets.ciciot2023.reader import CICIoT2023Reader
from datp_core.datasets.ciciot2023.schema import CICIOT2023_SCHEMA, CICIoT2023ArtifactName
from datp_core.datasets.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.datasets.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.datasets.edge_iiotset.reader import EdgeIIoTsetReader
from datp_core.datasets.edge_iiotset.schema import EDGE_SCHEMA, EdgeArtifactName, EdgeArtifactSuffix
from datp_core.datasets.models import CanonicalSchema, MaterializedDataset
from datp_core.datasets.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.datasets.nbaiot.materialize import NBaIoTMaterializer
from datp_core.datasets.nbaiot.reader import NBaIoTReader
from datp_core.datasets.nbaiot.schema import NBAIOT_SCHEMA, NBaIoTArtifactName
from datp_core.domain.enums import DatasetId

type DatasetPublication = MaterializedDataset[StrEnum, StrEnum]


@dataclass(frozen=True, slots=True)
class DatasetBinding:
    reader: NBaIoTReader | CICIoT2023Reader | EdgeIIoTsetReader
    materializer: NBaIoTMaterializer | CICIoT2023Materializer | EdgeIIoTsetMaterializer
    capabilities: DatasetCapabilities
    schema: CanonicalSchema
    publish: Callable[[Path, Path], DatasetPublication]


def dataset_binding(dataset_id: DatasetId) -> DatasetBinding:
    try:
        return _DATASET_BINDINGS[dataset_id]
    except KeyError as error:
        raise ValueError(f"unsupported dataset identity: {dataset_id}") from error


def _publish_nbaiot(raw_root: Path, canonical_root: Path) -> DatasetPublication:
    sources = tuple(
        path
        for path in sorted(raw_root.glob(f"**/*{NBaIoTArtifactName.CSV_SUFFIX}"))
        if path.name != NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
    )
    return NBaIoTMaterializer().materialize(sources, canonical_root)


def _publish_ciciot2023(raw_root: Path, canonical_root: Path) -> DatasetPublication:
    sources = tuple(sorted(raw_root.glob(f"**/{CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY}/*.csv")))
    return CICIoT2023Materializer().materialize(sources, canonical_root)


def _publish_edge_iiotset(raw_root: Path, canonical_root: Path) -> DatasetPublication:
    bundle_root = raw_root / EdgeArtifactName.DATASET_BUNDLE_DIRECTORY
    benign = tuple(
        sorted((bundle_root / EdgeArtifactName.NORMAL_TRAFFIC_DIRECTORY).glob(f"*/*{EdgeArtifactSuffix.CSV}"))
    )
    attacks = tuple(
        sorted(
            (bundle_root / EdgeArtifactName.ATTACK_TRAFFIC_DIRECTORY).glob(f"*{EdgeArtifactName.ATTACK_FILE_SUFFIX}")
        )
    )
    return EdgeIIoTsetMaterializer().materialize(benign, attacks, canonical_root)


_DATASET_BINDINGS: dict[DatasetId, DatasetBinding] = {
    DatasetId.NBAIOT: DatasetBinding(
        NBaIoTReader(), NBaIoTMaterializer(), NBAIOT_CAPABILITIES, NBAIOT_SCHEMA, _publish_nbaiot
    ),
    DatasetId.CICIOT2023: DatasetBinding(
        CICIoT2023Reader(), CICIoT2023Materializer(), CICIOT2023_CAPABILITIES, CICIOT2023_SCHEMA, _publish_ciciot2023
    ),
    DatasetId.EDGE_IIOTSET: DatasetBinding(
        EdgeIIoTsetReader(), EdgeIIoTsetMaterializer(), EDGE_IIOTSET_CAPABILITIES, EDGE_SCHEMA, _publish_edge_iiotset
    ),
}
