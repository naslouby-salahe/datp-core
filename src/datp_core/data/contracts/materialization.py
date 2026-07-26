"""Materialization-related contract records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from attrs import define, field

from datp_core.core.identifiers import MaterializationId
from datp_core.core.immutability import (
    FrozenJson,
    as_optional_frozen_json_mapping,
    as_optional_int_mapping,
    as_optional_str_mapping,
    deep_freeze,
)
from datp_core.core.numbers import PositiveInt, Probability
from datp_core.core.seeding import Seed
from datp_core.data.contracts.enums import (
    ClientConstructionMethod,
    NormalizationFitScope,
    NormalizationStrategy,
    SplitMembership,
    SplitMethod,
)


@define(frozen=True, slots=True, kw_only=True)
class SetupClientConstructionRecord:
    method: ClientConstructionMethod
    client_source: str | tuple[str, ...] | None
    client_semantics: str | None
    excluded_client_folders: tuple[str, ...] | None
    client_count: PositiveInt | None
    partition_condition: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    source_mixture_components: str | None
    label_field: str | None
    partition_seed: Seed | None
    partition_axes: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    allocation_procedure: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    same_proportions_govern: tuple[str, ...] | None
    split_role_preservation: str | None
    attack_row_assignment: str | None
    attack_labels_used_in_partition_generation: bool | None
    minimum_row_counts: Mapping[str, int] | None = field(converter=as_optional_int_mapping)
    retry_policy: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    feasibility_failure: str | None
    manifest_invariants: tuple[str, ...] | None
    manifest_fields: tuple[str, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class PartitionSeedContract:
    key: str
    digest_bytes: PositiveInt


@define(frozen=True, slots=True, kw_only=True)
class DatasetMaterialization:
    identifier: MaterializationId
    role: str | None
    normalization_strategy: NormalizationStrategy
    normalization_scope: NormalizationFitScope
    vocabulary_fit_split: str | None
    preprocessing_sequence: tuple[str, ...]
    row_exclusion: Mapping[str, str | bool] = field(
        converter=lambda v: cast("Mapping[str, str | bool]", deep_freeze(v))
    )
    split_row_semantics: Mapping[str, str | bool] | None
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
    split_minimum_row_counts: Mapping[str, int] | None = field(converter=as_optional_int_mapping)
    split_missing_client_policy: str | None
    split_chronology_unverifiable_policy: str | None

    def ratio(self, role: str | SplitMembership) -> Probability:
        role_value = role.value if isinstance(role, SplitMembership) else role
        for configured_role, configured_ratio in self.split_ratios:
            if configured_role == role_value:
                return configured_ratio
        raise KeyError(
            f"Materialization '{self.identifier.value}' has no configured ratio for '{role_value}'")

    def chronological_ratio(self, role: str | SplitMembership) -> Probability:
        role_value = role.value if isinstance(role, SplitMembership) else role
        for configured_role, configured_ratio in self.chronological_ratios:
            if configured_role == role_value:
                return configured_ratio
        raise KeyError(
            f"Materialization '{self.identifier.value}' has no chronological ratio for '{role_value}'")
