"""N-BaIoT adapter."""

from datp_core.data.adapters.nbaiot.adapter import NBaIoTAdapter
from datp_core.data.adapters.nbaiot.models import (
    DirichletPartition,
    NBaIoTChronologicalBoundaries,
    NBaIoTMaterializedRow,
    NBaIoTSplitRows,
)
from datp_core.data.adapters.nbaiot.parquet import (
    consolidate_nbaiot_parquet_sources,
    encode_nbaiot_split_as_parquet,
    materialize_nbaiot_source_row,
    write_nbaiot_source_parquet,
)
from datp_core.data.adapters.nbaiot.partitioning import (
    apply_nbaiot_dirichlet_partition,
    derive_partition_seed,
    partition_dirichlet_rows,
)
from datp_core.data.adapters.nbaiot.splitting import (
    calculate_nbaiot_chronological_boundaries,
    random_fractional_roles,
    split_nbaiot_chronological_gapped_rows,
    split_nbaiot_using_resolved_materialization,
)

__all__ = [
    "DirichletPartition",
    "NBaIoTAdapter",
    "NBaIoTChronologicalBoundaries",
    "NBaIoTMaterializedRow",
    "NBaIoTSplitRows",
    "apply_nbaiot_dirichlet_partition",
    "calculate_nbaiot_chronological_boundaries",
    "consolidate_nbaiot_parquet_sources",
    "derive_partition_seed",
    "encode_nbaiot_split_as_parquet",
    "materialize_nbaiot_source_row",
    "partition_dirichlet_rows",
    "random_fractional_roles",
    "split_nbaiot_chronological_gapped_rows",
    "split_nbaiot_using_resolved_materialization",
    "write_nbaiot_source_parquet",
]
