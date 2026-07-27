"""Materialization-related contract records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import BeforeValidator

from datp_core.core.identifiers import MaterializationId
from datp_core.core.numbers import PositiveInt, Probability
from datp_core.core.seeding import Seed
from datp_core.data.contracts.enums import (
    ClientConstructionMethod,
    NormalizationFitScope,
    NormalizationStrategy,
    SplitMembership,
    SplitMethod,
)



_OptionalStrMappingField = Annotated[Mapping[str, str] | None, BeforeValidator(lambda v: dict(v) if v is not None else None)]
_OptionalIntMappingField = Annotated[Mapping[str, int] | None, BeforeValidator(lambda v: dict(v) if v is not None else None)]
_OptionalObjectMappingField = Annotated[
    Mapping[str, object] | None,
    BeforeValidator(lambda v: dict(v) if v is not None else None),
]
_RowExclusionField = Annotated[Mapping[str, str | bool], BeforeValidator(lambda v: dict(v))]


class SetupClientConstructionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: ClientConstructionMethod
    client_source: str | tuple[str, ...] | None
    client_semantics: str | None
    excluded_client_folders: tuple[str, ...] | None
    client_count: PositiveInt | None
    partition_condition: _OptionalStrMappingField
    source_mixture_components: str | None
    label_field: str | None
    partition_seed: Seed | None
    partition_axes: _OptionalStrMappingField
    allocation_procedure: _OptionalStrMappingField
    same_proportions_govern: tuple[str, ...] | None
    split_role_preservation: str | None
    attack_row_assignment: str | None
    attack_labels_used_in_partition_generation: bool | None
    minimum_row_counts: _OptionalIntMappingField
    retry_policy: _OptionalObjectMappingField
    feasibility_failure: str | None
    manifest_invariants: tuple[str, ...] | None
    manifest_fields: tuple[str, ...] | None


class PartitionSeedContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    digest_bytes: PositiveInt


class DatasetMaterialization(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: MaterializationId
    role: str | None
    normalization_strategy: NormalizationStrategy
    normalization_scope: NormalizationFitScope
    vocabulary_fit_split: str | None
    preprocessing_sequence: tuple[str, ...]
    row_exclusion: _RowExclusionField
    split_row_semantics: _OptionalStrMappingField
    infeasibility_policy: str | None
    split_method: SplitMethod
    split_seed: Seed | None
    split_ratios: tuple[tuple[str, Probability], ...]
    chronological_ratios: tuple[tuple[str, Probability], ...]
    split_ordering_basis: str | None
    split_ordering_scope: str | None
    split_gap_handling: str | None
    split_attack_rows: str | None
    split_attack_test_membership: str | None
    split_attack_ordering: str | None
    split_benign_attack_deduplication: str | None
    split_role_order: tuple[str, ...] | None
    split_excluded_client_folders: tuple[str, ...] | None
    split_exclusion_reason: str | None
    split_ordering_field: str | None
    split_ordering_sort: str | None
    split_rollover_policy: str | None
    split_rollover_scope: str | None
    split_boundary_rule: str | None
    split_boundary_index_formula: str | None
    split_future_leakage_check: str | None
    split_minimum_row_counts: _OptionalIntMappingField
    split_missing_client_policy: str | None
    split_chronology_unverifiable_policy: str | None

    def ratio(self, role: str | SplitMembership) -> Probability:
        role_value = role.value if isinstance(role, SplitMembership) else role
        for configured_role, configured_ratio in self.split_ratios:
            if configured_role == role_value:
                return configured_ratio
        raise KeyError(f"Materialization '{self.identifier.value}' has no configured ratio for '{role_value}'")

    def chronological_ratio(self, role: str | SplitMembership) -> Probability:
        role_value = role.value if isinstance(role, SplitMembership) else role
        for configured_role, configured_ratio in self.chronological_ratios:
            if configured_role == role_value:
                return configured_ratio
        raise KeyError(f"Materialization '{self.identifier.value}' has no chronological ratio for '{role_value}'")
