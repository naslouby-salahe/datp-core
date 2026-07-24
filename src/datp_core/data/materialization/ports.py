"""Materialization protocol ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts.dataset import DatasetSetup, ResolvedDataset
from datp_core.data.contracts.enums import AdapterKind
from datp_core.data.contracts.materialization import DatasetMaterialization, PartitionSeedContract
from datp_core.experiments import SweepConditionRecord


class SourceEntry(Protocol):
    @property
    def source_path(self) -> Path: ...
    @property
    def relative_path(self) -> Path: ...
    @property
    def source_tree_identifier(self) -> str: ...


class SourceInventory(Protocol):
    @property
    def dataset_id(self) -> DatasetId: ...
    @property
    def entries(self) -> tuple[SourceEntry, ...]: ...
    @property
    def file_count(self) -> int: ...


class MaterializationPayload(Protocol):
    @property
    def staged_path(self) -> Path: ...
    @property
    def row_count(self) -> int: ...
    @property
    def preprocessing_evidence(self) -> bytes: ...
    @property
    def partition_evidence(self) -> bytes | None: ...


class DatasetMaterializer(Protocol):
    @property
    def adapter_kind(self) -> AdapterKind: ...

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
        *,
        chunk_row_count: int,
    ) -> MaterializationPayload: ...
