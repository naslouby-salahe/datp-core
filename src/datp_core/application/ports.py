"""Application-facing port contracts for infrastructure capabilities.

Every port is a narrow Protocol that describes capability, not a concrete library.
Application use cases depend on these ports; the composition root wires concrete
implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import polars as pl

from datp_core.domain.datasets import (
    AdapterKind,
    DatasetMaterialization,
    DatasetSetup,
    ResolvedDataset,
)
from datp_core.domain.identifiers import DatasetId


class SourceEntry(Protocol):
    """One ordered, typed source file entry produced by the source-discovery authority."""

    @property
    def source_path(self) -> Path: ...
    @property
    def relative_path(self) -> Path: ...
    @property
    def source_tree_identifier(self) -> str: ...


class SourceInventory(Protocol):
    """Ordered, typed inventory of source files for one resolved dataset.

    Materialization consumes this ordered inventory rather than discovering
    source files independently.
    """

    @property
    def dataset_id(self) -> DatasetId: ...
    @property
    def entries(self) -> tuple[SourceEntry, ...]: ...
    @property
    def file_count(self) -> int: ...


class MaterializationPayload(Protocol):
    """Result of a dataset adapter materializing one dataset to a staging directory."""

    @property
    def staged_path(self) -> Path: ...
    @property
    def row_count(self) -> int: ...
    @property
    def preprocessing_evidence(self) -> bytes: ...


class DatasetMaterializer(Protocol):
    """Port for materializing one resolved dataset to a staged Parquet payload.

    Each adapter implementation handles exactly one AdapterKind.
    """

    @property
    def adapter_kind(self) -> AdapterKind: ...

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
    ) -> MaterializationPayload: ...


class ResultQueryService(Protocol):
    """Port for read-only result querying and completeness auditing.

    The concrete DuckDB implementation is wired in the composition root.
    """

    def execute_query(self, sql_query: str) -> pl.DataFrame: ...

    def audit_metrics_completeness(self, metrics_parquet_pattern: str, expected_seed_count: int) -> pl.DataFrame: ...
