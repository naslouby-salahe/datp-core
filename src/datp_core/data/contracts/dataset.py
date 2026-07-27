"""Resolved dataset and setup records."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import (
    ClientId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
)
from datp_core.core.paths import RelativePath
from datp_core.data.contracts.enums import AdapterKind
from datp_core.data.contracts.features import DatasetFieldSchemaRecord
from datp_core.data.contracts.materialization import (
    DatasetMaterialization,
    SetupClientConstructionRecord,
)
from datp_core.data.contracts.sources import (
    DatasetInspectionContract,
    DatasetSourceLayoutContractRecord,
    SourceContractRecord,
)
from datp_core.thresholding.models import FamilyAssignments


class ResolvedDatasetPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_data_root: Path
    raw_root: Path
    processed_root: Path


class SourceLayout(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: RelativePath
    ignored_suffixes: tuple[str, ...]
    ignored_subtrees: tuple[str, ...]


class DatasetSetup(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: DatasetSetupId
    materialization_id: MaterializationId
    capabilities: tuple[str, ...]
    client_construction: SetupClientConstructionRecord
    validation_scope: str | None
    eligibility_gate: str | None
    client_population_must_equal_setup: DatasetSetupId | None


class ResolvedDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: DatasetId
    adapter_kind: AdapterKind
    display_name: str
    schema_id: str
    source_layout: SourceLayout
    source_layout_contract: DatasetSourceLayoutContractRecord
    field_schema: DatasetFieldSchemaRecord
    source_contract: SourceContractRecord
    client_identity_contract: Mapping[str, object] | None
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

    @property
    def family_assignments(self) -> FamilyAssignments | None:
        family_map = self.field_schema.label_fields.family_map
        if not family_map:
            return None
        return FamilyAssignments(
            mapping=tuple((ClientId(k), v) for k, v in family_map.items())
        )
