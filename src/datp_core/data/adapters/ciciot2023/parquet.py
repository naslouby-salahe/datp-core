"""CICIoT2023 Parquet schema and Arrow serialization."""

# Re-exports from index module - Parquet serialization lives with the index
from datp_core.data.adapters.ciciot2023.index import (
    _deserialize_features,
    _serialize_features,
)

__all__ = [
    "_deserialize_features",
    "_serialize_features",
]
