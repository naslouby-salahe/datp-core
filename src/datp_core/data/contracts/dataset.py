"""Strict dataset and setup contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from datp_core.core.identifiers import (
    ClientId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
)
from datp_core.data.contracts.base import StrictFrozenModel
from datp_core.data.contracts.enums import AdapterKind, DatasetCapability
from datp_core.data.contracts.materialization import (
    ClientConstructionConfig,
    NormalizationConfig,
    OneHotEncodingConfig,
    SplitConfig,
)
from datp_core.data.contracts.sources import (
    CICIoT2023SourceConfig,
    EdgeIIoTsetSourceConfig,
    NBaIoTSourceConfig,
)
from datp_core.data.contracts.values import SchemaId


class DatasetSetupError(ValueError):
    pass


class ResolvedDatasetPaths(StrictFrozenModel):
    raw_data_root: Path
    processed_root: Path


class ClientFamilyAssignment(StrictFrozenModel):
    client_id: ClientId
    family: str

    @model_validator(mode="after")
    def validate_family(self) -> ClientFamilyAssignment:
        if not self.family.strip():
            raise ValueError("family must not be blank")
        return self


class DatasetSetup(StrictFrozenModel):
    identifier: DatasetSetupId
    materialization_id: MaterializationId
    capabilities: tuple[DatasetCapability, ...]
    client_construction: ClientConstructionConfig
    eligibility_policy_id: EligibilityPolicyId


class MaterializationDefinition(StrictFrozenModel):
    identifier: MaterializationId
    split: SplitConfig
    normalization: NormalizationConfig


class EdgeMaterializationDefinition(MaterializationDefinition):
    categorical_encoding: OneHotEncodingConfig


class _DatasetBase(StrictFrozenModel):
    def setup(self, setup_id: DatasetSetupId) -> DatasetSetup:
        for item in self.setups:  # type: ignore[attr-defined]
            if item.identifier == setup_id:
                return item
        raise DatasetSetupError(f"setup '{setup_id.value}' not found")

    def materialization(self, materialization_id: MaterializationId) -> MaterializationDefinition:
        for item in self.materializations:  # type: ignore[attr-defined]
            if item.identifier == materialization_id:
                return item
        raise DatasetSetupError(f"materialization '{materialization_id.value}' not found")


class CICIoT2023Dataset(_DatasetBase):
    adapter: Literal[AdapterKind.CICIOT2023]
    dataset_id: DatasetId
    display_name: str
    schema_id: SchemaId
    source: CICIoT2023SourceConfig
    paths: ResolvedDatasetPaths
    capabilities: tuple[DatasetCapability, ...]
    setups: tuple[DatasetSetup, ...]
    materializations: tuple[MaterializationDefinition, ...]
    family_assignments: tuple[ClientFamilyAssignment, ...]


class NBaIoTDataset(_DatasetBase):
    adapter: Literal[AdapterKind.NBAIOT]
    dataset_id: DatasetId
    display_name: str
    schema_id: SchemaId
    source: NBaIoTSourceConfig
    paths: ResolvedDatasetPaths
    capabilities: tuple[DatasetCapability, ...]
    setups: tuple[DatasetSetup, ...]
    materializations: tuple[MaterializationDefinition, ...]
    family_assignments: tuple[ClientFamilyAssignment, ...]


class EdgeIIoTsetDataset(_DatasetBase):
    adapter: Literal[AdapterKind.EDGE_IIOTSET]
    dataset_id: DatasetId
    display_name: str
    schema_id: SchemaId
    source: EdgeIIoTsetSourceConfig
    paths: ResolvedDatasetPaths
    capabilities: tuple[DatasetCapability, ...]
    setups: tuple[DatasetSetup, ...]
    materializations: tuple[EdgeMaterializationDefinition, ...]
    family_assignments: tuple[ClientFamilyAssignment, ...]


type ResolvedDataset = Annotated[
    CICIoT2023Dataset | NBaIoTDataset | EdgeIIoTsetDataset,
    Field(discriminator="adapter"),
]
