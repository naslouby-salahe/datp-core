"""Pure resolved dataset records used outside the configuration boundary."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import cast

from attrs import define, field

from datp_core.domain.identifiers import DatasetId, DatasetSetupId, EligibilityPolicyId, MaterializationId
from datp_core.domain.values import Probability, RelativePath, Seed, deep_freeze


class AdapterKind(Enum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


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
class ConfiguredSourceTree:
    """One read-only configured source tree and its schema expectation."""

    identifier: str
    root: RelativePath
    file_pattern: str
    expected_column_count: int
    executable: bool
    required_headers: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class DatasetInspectionContract:
    """Pure resolved source-integrity rules required before materialization."""

    source_trees: tuple[ConfiguredSourceTree, ...]
    require_identical_headers: bool
    device_directories: tuple[str, ...]
    benign_filename: str | None
    benign_file_required_per_device: bool
    attack_family_directories: tuple[str, ...]
    attack_family_required_per_device: bool
    normal_group_directories: tuple[str, ...]
    attack_filenames: tuple[str, ...]
    ignored_root_entries: tuple[str, ...]
    benign_label: str | None
    normal_traffic_root: RelativePath | None
    attack_traffic_root: RelativePath | None
    binary_label_header: str | None


@define(frozen=True, slots=True, kw_only=True)
class DatasetSetup:
    identifier: DatasetSetupId
    materialization_id: MaterializationId
    capabilities: tuple[str, ...]


def _as_mapping_str_str_or_bool(value: object) -> Mapping[str, str | bool]:
    return cast("Mapping[str, str | bool]", deep_freeze(value))


@define(frozen=True, slots=True, kw_only=True)
class DatasetMaterialization:
    identifier: MaterializationId
    role: str | None = None
    normalization_strategy: str
    normalization_scope: str
    vocabulary_fit_split: str | None = None
    preprocessing_sequence: tuple[str, ...]
    row_exclusion: Mapping[str, str | bool] = field(converter=_as_mapping_str_str_or_bool)
    split_row_semantics: Mapping[str, str | bool] | None = None
    infeasibility_policy: str | None = None
    split_method: str
    split_seed: Seed | None
    split_ratios: tuple[tuple[str, Probability], ...]
    chronological_ratios: tuple[tuple[str, Probability], ...] = ()
    split_ordering_basis: str | None = None
    split_ordering_scope: str | None = None
    split_gap_handling: str | None = None
    split_attack_rows: str | None = None
    split_attack_test_membership: str | None = None
    split_attack_ordering: str | None = None
    split_benign_attack_deduplication: str | None = None
    split_role_order: tuple[str, ...] | None = None
    split_excluded_client_folders: tuple[str, ...] | None = None
    split_exclusion_reason: str | None = None
    split_ordering_field: str | None = None
    split_ordering_sort: str | None = None
    split_rollover_policy: str | None = None
    split_rollover_scope: str | None = None
    split_boundary_rule: str | None = None
    split_boundary_index_formula: str | None = None
    split_future_leakage_check: str | None = None
    split_minimum_row_counts: Mapping[str, int] | None = None
    split_missing_client_policy: str | None = None
    split_chronology_unverifiable_policy: str | None = None

    def ratio(self, role: str) -> Probability:
        for configured_role, configured_ratio in self.split_ratios:
            if configured_role == role:
                return configured_ratio
        raise KeyError(f"Materialization '{self.identifier.value}' has no configured ratio for '{role}'")

    def chronological_ratio(self, role: str) -> Probability:
        for configured_role, configured_ratio in self.chronological_ratios:
            if configured_role == role:
                return configured_ratio
        raise KeyError(f"Materialization '{self.identifier.value}' has no chronological ratio for '{role}'")


@define(frozen=True, slots=True, kw_only=True)
class ResolvedDataset:
    dataset_id: DatasetId
    adapter_kind: AdapterKind
    display_name: str
    schema_id: str
    source_layout: SourceLayout
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
