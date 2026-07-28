"""Resolved execution plans and immutable materialization results."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

import msgspec

from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import DatasetId, DatasetSetupId, MaterializationId
from datp_core.data.contracts.eligibility import EligibilityPolicy, ReadinessGate
from datp_core.data.contracts.enums import (
    AdapterKind,
    DatasetCapability,
    DatasetPlanKind,
    MaterializedArtifactShape,
    StagingArtifactName,
)
from datp_core.data.contracts.materialization import (
    DataLoadingConfig,
    DatasetFileClientConfig,
    DirichletClientConfig,
    NormalizationConfig,
    OneHotEncodingConfig,
    PartitionCondition,
    PhysicalDeviceClientConfig,
    RandomFractionalSplitConfig,
    SensorGroupClientConfig,
    SplitConfig,
)
from datp_core.data.contracts.sources import (
    CICIoT2023SourceConfig,
    EdgeIIoTsetSourceConfig,
    NBaIoTSourceConfig,
)
from datp_core.data.sources.models import SourceInventory
from datp_core.pipeline.stages.context import DataContext


class MaterializationArtifactLayout(msgspec.Struct, frozen=True):
    database: Path
    temporary_directory: Path
    raw_payload: Path
    encoded_payload: Path
    final_payload: Path

    @classmethod
    def for_staging_root(cls, staging_root: Path) -> MaterializationArtifactLayout:
        return cls(
            database=staging_root / StagingArtifactName.DATABASE.value,
            temporary_directory=staging_root / StagingArtifactName.TEMPORARY_DIRECTORY.value,
            raw_payload=staging_root / StagingArtifactName.RAW_PAYLOAD.value,
            encoded_payload=staging_root / StagingArtifactName.ENCODED_PAYLOAD.value,
            final_payload=staging_root / StagingArtifactName.FINAL_PAYLOAD.value,
        )


class PlanIdentity(msgspec.Struct, frozen=True):
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    materialization_id: MaterializationId
    configuration_checksum: Checksum


class CICIoT2023MaterializationPlan(msgspec.Struct, frozen=True):
    kind: Literal[DatasetPlanKind.CICIOT2023]
    identity: PlanIdentity
    adapter: Literal[AdapterKind.CICIOT2023]
    source: CICIoT2023SourceConfig
    raw_data_root: Path
    split: RandomFractionalSplitConfig
    normalization: NormalizationConfig
    client_construction: DatasetFileClientConfig
    eligibility: EligibilityPolicy
    readiness_gates: tuple[ReadinessGate, ...]
    capabilities: tuple[DatasetCapability, ...]
    expected_client_count: int
    runtime: DataLoadingConfig
    staging_parent: Path
    artifact_shape: Literal[MaterializedArtifactShape.CICIOT2023]


class NBaIoTPhysicalMaterializationPlan(msgspec.Struct, frozen=True):
    kind: Literal[DatasetPlanKind.NBAIOT_PHYSICAL]
    identity: PlanIdentity
    adapter: Literal[AdapterKind.NBAIOT]
    source: NBaIoTSourceConfig
    raw_data_root: Path
    split: SplitConfig
    normalization: NormalizationConfig
    client_construction: PhysicalDeviceClientConfig
    eligibility: EligibilityPolicy
    readiness_gates: tuple[ReadinessGate, ...]
    capabilities: tuple[DatasetCapability, ...]
    expected_client_count: int
    runtime: DataLoadingConfig
    staging_parent: Path
    artifact_shape: Literal[MaterializedArtifactShape.NBAIOT]


class NBaIoTDirichletMaterializationPlan(msgspec.Struct, frozen=True):
    kind: Literal[DatasetPlanKind.NBAIOT_DIRICHLET]
    identity: PlanIdentity
    adapter: Literal[AdapterKind.NBAIOT]
    source: NBaIoTSourceConfig
    raw_data_root: Path
    split: SplitConfig
    normalization: NormalizationConfig
    client_construction: DirichletClientConfig
    partition_condition: PartitionCondition
    eligibility: EligibilityPolicy
    readiness_gates: tuple[ReadinessGate, ...]
    capabilities: tuple[DatasetCapability, ...]
    expected_client_count: int
    runtime: DataLoadingConfig
    staging_parent: Path
    artifact_shape: Literal[MaterializedArtifactShape.NBAIOT]


class EdgeIIoTsetMaterializationPlan(msgspec.Struct, frozen=True):
    kind: Literal[DatasetPlanKind.EDGE_IIOTSET]
    identity: PlanIdentity
    adapter: Literal[AdapterKind.EDGE_IIOTSET]
    source: EdgeIIoTsetSourceConfig
    raw_data_root: Path
    split: SplitConfig
    normalization: NormalizationConfig
    categorical_encoding: OneHotEncodingConfig
    client_construction: SensorGroupClientConfig
    eligibility: EligibilityPolicy
    readiness_gates: tuple[ReadinessGate, ...]
    capabilities: tuple[DatasetCapability, ...]
    expected_client_count: int
    runtime: DataLoadingConfig
    staging_parent: Path
    artifact_shape: MaterializedArtifactShape


type DatasetMaterializationPlan = (
    CICIoT2023MaterializationPlan
    | NBaIoTPhysicalMaterializationPlan
    | NBaIoTDirichletMaterializationPlan
    | EdgeIIoTsetMaterializationPlan
)


class MaterializationRequest(msgspec.Struct, frozen=True):
    plan: DatasetMaterializationPlan
    inventory: SourceInventory
    staging_root: Path
    layout: MaterializationArtifactLayout


class MaterializationEvidence(msgspec.Struct, frozen=True):
    schema_version: str
    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int
    written_rows: int
    encoded_feature_names: tuple[str, ...]


class StandardMaterializationResult(msgspec.Struct, frozen=True):
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    materialization_evidence: MaterializationEvidence


class PartitionedMaterializationResult(msgspec.Struct, frozen=True):
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes
    materialization_evidence: MaterializationEvidence


type MaterializationResult = StandardMaterializationResult | PartitionedMaterializationResult


class DatasetMaterializer(Protocol):
    @property
    def adapter_kind(self) -> AdapterKind: ...

    def materialize(self, request: MaterializationRequest) -> MaterializationResult: ...


class MaterializationPlanResolver(Protocol):
    def resolve(self, context: DataContext) -> DatasetMaterializationPlan: ...


class SourceFingerprintObservation(msgspec.Struct, frozen=True):
    before: Checksum
    after: Checksum
