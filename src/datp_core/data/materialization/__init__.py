"""Materialization ports, models, registry, and handler."""

from datp_core.data.materialization.ports import (
    DatasetMaterializer,
    MaterializationPayload,
    SourceEntry,
    SourceInventory,
)
from datp_core.data.materialization.models import MaterializationResult
from datp_core.data.materialization.registry import DatasetAdapterRegistry
from datp_core.data.materialization.handler import DatasetMaterializationStageHandler

__all__ = [
    "DatasetAdapterRegistry",
    "DatasetMaterializationStageHandler",
    "DatasetMaterializer",
    "MaterializationPayload",
    "MaterializationResult",
    "SourceEntry",
    "SourceInventory",
]
