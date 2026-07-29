"""Exhaustive typed dataset dispatch."""

from dataclasses import dataclass

from datp_core.datasets.capabilities import DatasetCapabilities
from datp_core.datasets.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.datasets.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.datasets.ciciot2023.reader import CICIoT2023Reader
from datp_core.datasets.ciciot2023.schema import CICIOT2023_SCHEMA
from datp_core.datasets.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.datasets.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.datasets.edge_iiotset.reader import EdgeIIoTsetReader
from datp_core.datasets.edge_iiotset.schema import EDGE_SCHEMA
from datp_core.datasets.models import CanonicalSchema
from datp_core.datasets.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.datasets.nbaiot.materialize import NBaIoTMaterializer
from datp_core.datasets.nbaiot.reader import NBaIoTReader
from datp_core.datasets.nbaiot.schema import NBAIOT_SCHEMA
from datp_core.domain.enums import DatasetId


@dataclass(frozen=True, slots=True)
class DatasetBinding:
    reader: NBaIoTReader | CICIoT2023Reader | EdgeIIoTsetReader
    materializer: NBaIoTMaterializer | CICIoT2023Materializer | EdgeIIoTsetMaterializer
    capabilities: DatasetCapabilities
    schema: CanonicalSchema


def dataset_binding(dataset_id: DatasetId) -> DatasetBinding:
    match dataset_id:
        case DatasetId.NBAIOT:
            return DatasetBinding(NBaIoTReader(), NBaIoTMaterializer(), NBAIOT_CAPABILITIES, NBAIOT_SCHEMA)
        case DatasetId.CICIOT2023:
            return DatasetBinding(
                CICIoT2023Reader(), CICIoT2023Materializer(), CICIOT2023_CAPABILITIES, CICIOT2023_SCHEMA
            )
        case DatasetId.EDGE_IIOTSET:
            return DatasetBinding(
                EdgeIIoTsetReader(), EdgeIIoTsetMaterializer(), EDGE_IIOTSET_CAPABILITIES, EDGE_SCHEMA
            )
        case _:
            raise ValueError(f"unsupported dataset identity: {dataset_id}")
