"""Framework-free resolved catalogue records; Pydantic never crosses this boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ..kernel.fingerprints import Fingerprint
from ..kernel.ids import DatasetId, ExperimentId, PopulationId, RegistryId
from ..kernel.values import FrozenRegistry, PositiveInt, StructuredValue


@dataclass(frozen=True, slots=True, kw_only=True)
class Definition:
    identifier: RegistryId[object]
    kind: str
    values: Mapping[str, StructuredValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetDefinition:
    identifier: DatasetId
    display_name: str
    schema_id: RegistryId[object]
    source_layout: Mapping[str, StructuredValue]
    field_schema: Mapping[str, StructuredValue]
    source_contract: Mapping[str, StructuredValue]
    materializations: FrozenRegistry[RegistryId[object], Definition]
    setups: FrozenRegistry[RegistryId[object], Definition]

    def __post_init__(self) -> None:
        for field in ("source_layout", "field_schema", "source_contract"):
            object.__setattr__(self, field, MappingProxyType(dict(getattr(self, field))))


@dataclass(frozen=True, slots=True, kw_only=True)
class PopulationDefinition:
    identifier: PopulationId
    dataset_id: DatasetId
    setup_id: RegistryId[object]
    metric_bundle_id: RegistryId[object]


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationDefinition:
    identifier: RegistryId[object]
    threshold_policy_id: RegistryId[object]
    values: Mapping[str, StructuredValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentDefinition:
    identifier: ExperimentId
    display_name: str
    evidence_role: str
    run_requirement: str
    population_ids: tuple[PopulationId, ...]
    training_profile_id: RegistryId[object]
    checkpoint_profile_id: RegistryId[object]
    seed_cohort_id: RegistryId[object]
    eligibility_policy_id: RegistryId[object]
    prerequisite_ids: tuple[ExperimentId, ...]
    evaluations: tuple[EvaluationDefinition, ...]
    analyses: tuple[Definition, ...]
    report_profile_ids: tuple[RegistryId[object], ...]
    values: Mapping[str, StructuredValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtocolCatalogue:
    groups: Mapping[str, FrozenRegistry[RegistryId[object], Definition]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "groups", MappingProxyType(dict(self.groups)))

    def group(self, name: str) -> FrozenRegistry[RegistryId[object], Definition]:
        return self.groups[name]


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedStudyCatalogue:
    schema_version: PositiveInt
    datasets: FrozenRegistry[DatasetId, DatasetDefinition]
    protocols: ProtocolCatalogue
    populations: FrozenRegistry[PopulationId, PopulationDefinition]
    experiments: FrozenRegistry[ExperimentId, ExperimentDefinition]
    declared_capabilities: frozenset[str]
    catalogue_fingerprint: Fingerprint


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedRuntimeCatalogue:
    roots: Mapping[str, StructuredValue]
    execution_profiles: FrozenRegistry[RegistryId[object], Definition]
    runtime_fingerprint: Fingerprint

    def __post_init__(self) -> None:
        object.__setattr__(self, "roots", MappingProxyType(dict(self.roots)))


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedConfiguration:
    study: ResolvedStudyCatalogue
    runtime: ResolvedRuntimeCatalogue
