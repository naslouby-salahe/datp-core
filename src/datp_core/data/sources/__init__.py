"""Shared data source behaviors: inventory, CSV parsing, and streaming."""

from datp_core.data.sources.models import (
    ConcreteSourceEntry,
    ConcreteSourceInventory,
    CsvValidationResult,
    LabeledSourceRow,
    SourceRow,
    SourceRowFailure,
)
from datp_core.data.sources.inventory import build_source_inventory
from datp_core.data.sources.csv import (
    iter_labeled_numeric_csv_source,
    iter_numeric_csv_source,
    read_numeric_csv_source,
)

__all__ = [
    "ConcreteSourceEntry",
    "ConcreteSourceInventory",
    "CsvValidationResult",
    "LabeledSourceRow",
    "SourceRow",
    "SourceRowFailure",
    "build_source_inventory",
    "iter_labeled_numeric_csv_source",
    "iter_numeric_csv_source",
    "read_numeric_csv_source",
]
