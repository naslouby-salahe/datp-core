"""Data contracts: resolved dataset contracts, enums, and configuration records."""

from datp_core.data.contracts.dataset import (
    DatasetSetup,
    ResolvedDataset,
    ResolvedDatasetPaths,
    SourceLayout,
)
from datp_core.data.contracts.eligibility import (
    EligibilityFallbackRecord,
    EligibilityPolicyRecord,
    NormalizationStrategyRecord,
)
from datp_core.data.contracts.enums import (
    AdapterKind,
    ClientConstructionMethod,
    NormalizationFitScope,
    NormalizationStrategy,
    SplitMembership,
    SplitMethod,
)
from datp_core.data.contracts.features import (
    CategoricalEncodingRecord,
    DatasetFieldSchemaRecord,
    EndpointIdentityRecord,
    IdentitySchemeRecord,
    LabelFieldsRecord,
    ModelFeaturesRecord,
    MulticlassLabelRecord,
    RetainedNumericFeaturesRecord,
)
from datp_core.data.contracts.materialization import (
    DatasetMaterialization,
    PartitionSeedContract,
    SetupClientConstructionRecord,
)
from datp_core.data.contracts.sources import (
    ConfiguredSourceTree,
    CrossSourceRelationshipRecord,
    DatasetInspectionContract,
    DatasetSourceLayoutContractRecord,
    DatasetSourceRecord,
    SourceContractRecord,
)

__all__ = [
    "AdapterKind",
    "CategoricalEncodingRecord",
    "ClientConstructionMethod",
    "ConfiguredSourceTree",
    "CrossSourceRelationshipRecord",
    "DatasetFieldSchemaRecord",
    "DatasetInspectionContract",
    "DatasetMaterialization",
    "DatasetSetup",
    "DatasetSourceLayoutContractRecord",
    "DatasetSourceRecord",
    "EligibilityFallbackRecord",
    "EligibilityPolicyRecord",
    "EndpointIdentityRecord",
    "IdentitySchemeRecord",
    "LabelFieldsRecord",
    "ModelFeaturesRecord",
    "MulticlassLabelRecord",
    "NormalizationFitScope",
    "NormalizationStrategy",
    "NormalizationStrategyRecord",
    "PartitionSeedContract",
    "ResolvedDataset",
    "ResolvedDatasetPaths",
    "RetainedNumericFeaturesRecord",
    "SetupClientConstructionRecord",
    "SourceContractRecord",
    "SourceLayout",
    "SplitMembership",
    "SplitMethod",
]
