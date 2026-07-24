"""CICIoT2023 adapter."""

from datp_core.data.adapters.ciciot2023.adapter import CICIoT2023Adapter
from datp_core.data.adapters.ciciot2023.identity import (
    materialize_ciciot2023_merged_identity,
    materialize_ciciot2023_merged_source_row,
)
from datp_core.data.adapters.ciciot2023.index import (
    write_ciciot2023_materialized_parquet,
)
from datp_core.data.adapters.ciciot2023.models import (
    CICIoT2023DeduplicationResult,
    CICIoT2023MaterializationReport,
    CICIoT2023MaterializedRow,
    CICIoT2023RowIdentity,
    CICIoT2023SplitRows,
)
from datp_core.data.adapters.ciciot2023.splitting import (
    canonicalize_and_split_ciciot2023_rows,
)

__all__ = [
    "CICIoT2023Adapter",
    "CICIoT2023DeduplicationResult",
    "CICIoT2023MaterializationReport",
    "CICIoT2023MaterializedRow",
    "CICIoT2023RowIdentity",
    "CICIoT2023SplitRows",
    "canonicalize_and_split_ciciot2023_rows",
    "materialize_ciciot2023_merged_identity",
    "materialize_ciciot2023_merged_source_row",
    "write_ciciot2023_materialized_parquet",
]
