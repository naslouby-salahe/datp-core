"""Resolved dataset and setup records."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.core.identifiers import (
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
)
from datp_core.core.paths import RelativePath
from datp_core.data.contracts.enums import AdapterKind
from datp_core.data.contracts.features import DatasetFieldSchemaRecord
from datp_core.data.contracts.materialization import DatasetMaterialization, SetupClientConstructionRecord
from datp_core.data.contracts.sources import (
    DatasetInspectionContract,
    DatasetSourceLayoutContractRecord,
    SourceContractRecord,
)


@define(frozen=True, slots=True, kw_only=True)
class ResolvedDatasetPaths:
    raw_data_root: Path
    raw_root: Path
    processed_root: Path


@define(frozen=True, slots=True, kw_only=True)
class SourceLayout:
    root: RelativePath
    ignored_suffixes: tuple[str, ...]
    ignored_subtrees: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class DatasetSetup:
    identifier: DatasetSetupId
    materialization_id: MaterializationId
    capabilities: tuple[str, ...]
    client_construction: SetupClientConstructionRecord
    validation_scope: str | None
    eligibility_gate: str | None
    client_population_must_equal_setup: DatasetSetupId | None


@define(frozen=True, slots=True, kw_only=True)
class ResolvedDataset:
    dataset_id: DatasetId
    adapter_kind: AdapterKind
    display_name: str
    schema_id: str
    source_layout: SourceLayout
    source_layout_contract: DatasetSourceLayoutContractRecord
    field_schema: DatasetFieldSchemaRecord
    source_contract: SourceContractRecord
    client_identity_contract: object | None
    inspection_contract: DatasetInspectionContract
    setups: tuple[DatasetSetup, ...]
    materializations: tuple[DatasetMaterialization, ...]
    eligibility_policy_id: EligibilityPolicyId
    capabilities: tuple[str, ...]
    paths: ResolvedDatasetPaths
    fingerprint_source_fields: tuple[str, ...]
    fingerprint_schema_fields: tuple[str, ...]
    fingerprint_materialization_fields: tuple[str, ...]
    fingerprint_client_assignment_fields: tuple[str, ...]

    def setup(self, identifier: DatasetSetupId) -> DatasetSetup:
        for setup in self.setups:
            if setup.identifier == identifier:
                return setup
        raise KeyError(f"Dataset setup not registered: {identifier}")
