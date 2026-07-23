"""Dataset-resolution functions extracted from the monolithic resolver.

Ownership boundary: converts authored dataset Pydantic models into immutable
domain records owned by ``datasets/models.py``. Exports a narrow function surface;
does not import pipeline execution, CLI, or infrastructure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from datp_core.configuration.loading import ConfigurationError
from datp_core.configuration.models import (
    CategoricalEncodingConfig,
    DatasetFieldSchemaConfig,
    DatasetSourceLayoutConfig,
    EndpointIdentityConfig,
    IdentitySchemeConfig,
    LabelFieldsConfig,
    SetupClientConstructionConfig,
    SourceContractConfig,
)
from datp_core.configuration.runtime_resolution import ResolvedProjectPaths
from datp_core.datasets.models import (
    AdapterKind,
    CategoricalEncodingRecord,
    ConfiguredSourceTree,
    CrossSourceRelationshipRecord,
    DatasetFieldSchemaRecord,
    DatasetInspectionContract,
    DatasetMaterialization,
    DatasetSetup,
    DatasetSourceLayoutContractRecord,
    DatasetSourceRecord,
    EndpointIdentityRecord,
    IdentitySchemeRecord,
    LabelFieldsRecord,
    ModelFeaturesRecord,
    MulticlassLabelRecord,
    ResolvedDataset,
    ResolvedDatasetPaths,
    RetainedNumericFeaturesRecord,
    SetupClientConstructionRecord,
    SourceContractRecord,
    SourceLayout,
)
from datp_core.pipeline.identifiers import (
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
)
from datp_core.pipeline.values import (
    PositiveInt,
    Probability,
    RelativePath,
    Seed,
    as_optional_frozen_json_mapping,
    deep_freeze,
)


def resolve_identity_scheme(cfg: IdentitySchemeConfig) -> IdentitySchemeRecord:
    return IdentitySchemeRecord(
        row_identity=cfg.row_identity,
        client_identity=cfg.client_identity,
        benign_group_identity=cfg.benign_group_identity,
        attack_row_group_identity=cfg.attack_row_group_identity,
        label_identity=cfg.label_identity,
        attack_family_identity=cfg.attack_family_identity,
        attack_type_identity=cfg.attack_type_identity,
        device_identity=cfg.device_identity,
        device_mac_ip_field=cfg.device_mac_ip_field,
        timestamp_field=cfg.timestamp_field,
        chronological_ordering_basis=cfg.chronological_ordering_basis,
        provenance_fields=tuple(cfg.provenance_fields),
    )


def resolve_label_fields(cfg: LabelFieldsConfig) -> LabelFieldsRecord:
    multiclass = cfg.multiclass_label
    return LabelFieldsRecord(
        binary_label=cfg.binary_label,
        multiclass_label=(
            MulticlassLabelRecord(column=multiclass.column, type=multiclass.type, case=multiclass.case)
            if multiclass is not None
            else None
        ),
        benign_value=cfg.benign_value,
        attack_class_mapping=cfg.attack_class_mapping,
        device_family_mapping=cfg.device_family_mapping,
        family_taxonomy=cfg.family_taxonomy,
        family_map=cfg.family_map,
    )


def resolve_endpoint_identity(cfg: EndpointIdentityConfig) -> EndpointIdentityRecord:
    return EndpointIdentityRecord(
        resolution=cfg.resolution,
        fields=tuple(cfg.fields),
        internal_prefix=cfg.internal_prefix,
        subnet_component=cfg.subnet_component,
        subnet_role_source=cfg.subnet_role_source,
        subnet_to_group=cfg.subnet_to_group,
        excluded_endpoints=cfg.excluded_endpoints,
        direction_normalization=cfg.direction_normalization,
        use=cfg.use,
        unresolved_row_policy=cfg.unresolved_row_policy,
    )


def resolve_categorical_encoding(cfg: CategoricalEncodingConfig) -> CategoricalEncodingRecord:
    return CategoricalEncodingRecord(
        strategy=cfg.strategy,
        columns=tuple(cfg.columns),
        vocabulary_scope=cfg.vocabulary_scope,
        vocabulary_artifact=cfg.vocabulary_artifact,
        vocabulary_fingerprint=cfg.vocabulary_fingerprint,
        category_order=cfg.category_order,
        encoded_feature_naming=cfg.encoded_feature_naming,
        missing_category_policy=cfg.missing_category_policy,
        unknown_category_policy=cfg.unknown_category_policy,
        unknown_indicator_distinct_from_missing_indicator=cfg.unknown_indicator_distinct_from_missing_indicator,
        feature_order=tuple(cfg.feature_order),
    )


def resolve_field_schema(cfg: DatasetFieldSchemaConfig) -> DatasetFieldSchemaRecord:
    model_features = cfg.model_features
    retained_numeric_features = cfg.retained_numeric_features
    endpoint_identity = cfg.endpoint_identity
    return DatasetFieldSchemaRecord(
        source_column_count=cfg.source_column_count,
        header_required=cfg.header_required,
        header_must_be_identical_across_all_source_files=cfg.header_must_be_identical_across_all_source_files,
        header_must_be_identical_across_all_files_in_a_tree=cfg.header_must_be_identical_across_all_files_in_a_tree,
        merged_header_extends_per_class_header_with=cfg.merged_header_extends_per_class_header_with,
        label_column_position=cfg.label_column_position,
        identity_scheme=resolve_identity_scheme(cfg.identity_scheme),
        label_fields=resolve_label_fields(cfg.label_fields),
        model_features=(
            ModelFeaturesRecord(role=model_features.role, type=model_features.type, order=tuple(model_features.order))
            if model_features is not None
            else None
        ),
        source_columns=tuple(cfg.source_columns) if cfg.source_columns is not None else None,
        endpoint_identity=(resolve_endpoint_identity(endpoint_identity) if endpoint_identity is not None else None),
        attack_row_group_policy=cfg.attack_row_group_policy,
        retained_numeric_features=(
            RetainedNumericFeaturesRecord(
                role=retained_numeric_features.role,
                order=tuple(retained_numeric_features.order),
                numeric_parsing=retained_numeric_features.numeric_parsing,
                on_invalid_value=retained_numeric_features.on_invalid_value,
            )
            if retained_numeric_features is not None
            else None
        ),
        post_encoding_feature_order=cfg.post_encoding_feature_order,
        categorical_encoding=(
            cfg.categorical_encoding
            if isinstance(cfg.categorical_encoding, str)
            else resolve_categorical_encoding(cfg.categorical_encoding)
        ),
        leakage_exclusions=cfg.leakage_exclusions,
    )


def resolve_source_layout_contract(cfg: DatasetSourceLayoutConfig) -> DatasetSourceLayoutContractRecord:
    cross_source_relationship = cfg.cross_source_relationship
    return DatasetSourceLayoutContractRecord(
        root=RelativePath(cfg.root),
        benign_file=cfg.benign_file,
        benign_file_pattern=cfg.benign_file_pattern,
        normal_file_pattern=cfg.normal_file_pattern,
        attack_file_pattern=cfg.attack_file_pattern,
        device_dirs=tuple(cfg.device_dirs) if cfg.device_dirs is not None else None,
        normal_group_folders=tuple(cfg.normal_group_folders) if cfg.normal_group_folders is not None else None,
        executable_group_folders=(
            tuple(cfg.executable_group_folders) if cfg.executable_group_folders is not None else None
        ),
        attack_files=tuple(cfg.attack_files) if cfg.attack_files is not None else None,
        ignored_source_suffixes=tuple(cfg.ignored_source_suffixes),
        ignored_root_entries=tuple(cfg.ignored_root_entries),
        ignored_subtrees=tuple(cfg.ignored_subtrees),
        sources=(
            {
                key: DatasetSourceRecord(
                    role=source.role,
                    root=RelativePath(source.root),
                    file_pattern=source.file_pattern,
                    owns=tuple(source.owns) if source.owns is not None else None,
                    permitted_uses=tuple(source.permitted_uses) if source.permitted_uses is not None else None,
                    contributes_rows_to_executable_materializations=(
                        source.contributes_rows_to_executable_materializations
                    ),
                    defines_pseudo_clients=source.defines_pseudo_clients,
                )
                for key, source in cfg.sources.items()
            }
            if cfg.sources is not None
            else None
        ),
        executable_source=cfg.executable_source,
        cross_source_relationship=(
            CrossSourceRelationshipRecord(
                row_count_equality_required=cross_source_relationship.row_count_equality_required,
                row_level_one_to_one_equivalence_assumed=(
                    cross_source_relationship.row_level_one_to_one_equivalence_assumed
                ),
                join_by_row_position=cross_source_relationship.join_by_row_position,
                join_by_any_key=cross_source_relationship.join_by_any_key,
            )
            if cross_source_relationship is not None
            else None
        ),
        normal_traffic_root=(RelativePath(cfg.normal_traffic_root) if cfg.normal_traffic_root is not None else None),
        attack_traffic_root=(RelativePath(cfg.attack_traffic_root) if cfg.attack_traffic_root is not None else None),
        benign_file_required_per_device=cfg.benign_file_required_per_device,
        attack_family_dirs=tuple(cfg.attack_family_dirs) if cfg.attack_family_dirs is not None else None,
        attack_family_required_per_device=cfg.attack_family_required_per_device,
    )


def resolve_source_contract(cfg: SourceContractConfig) -> SourceContractRecord:
    return SourceContractRecord(
        every_model_feature_present_in_merged_header=cfg.every_model_feature_present_in_merged_header,
        every_model_feature_present_in_every_file=cfg.every_model_feature_present_in_every_file,
        model_feature_count_equals_source_column_count=cfg.model_feature_count_equals_source_column_count,
        per_class_schema_reference_check=cfg.per_class_schema_reference_check,
        malformed_row=cfg.malformed_row,
        empty_label_row=cfg.empty_label_row,
        reject_unparseable_numeric_model_feature=cfg.reject_unparseable_numeric_model_feature,
        reject_row_with_field_count_other_than_header=cfg.reject_row_with_field_count_other_than_header,
        column_role_partition=cfg.column_role_partition,
        positional_contract=cfg.positional_contract,
        row_integrity_exclusions=cfg.row_integrity_exclusions,
    )


def resolve_client_construction(cfg: SetupClientConstructionConfig) -> SetupClientConstructionRecord:
    client_source: str | tuple[str, ...] | None
    if cfg.client_source is None or isinstance(cfg.client_source, str):
        client_source = cfg.client_source
    else:
        client_source = tuple(cfg.client_source)
    return SetupClientConstructionRecord(
        method=cfg.method,
        client_source=client_source,
        client_semantics=cfg.client_semantics,
        excluded_client_folders=(
            tuple(cfg.excluded_client_folders) if cfg.excluded_client_folders is not None else None
        ),
        client_count=PositiveInt(cfg.client_count) if cfg.client_count is not None else None,
        partition_condition=cfg.partition_condition,
        source_mixture_components=cfg.source_mixture_components,
        label_field=cfg.label_field,
        partition_seed=Seed(cfg.partition_seed) if cfg.partition_seed is not None else None,
        partition_axes=cfg.partition_axes,
        allocation_procedure=cfg.allocation_procedure,
        same_proportions_govern=(
            tuple(cfg.same_proportions_govern) if cfg.same_proportions_govern is not None else None
        ),
        split_role_preservation=cfg.split_role_preservation,
        attack_row_assignment=cfg.attack_row_assignment,
        attack_labels_used_in_partition_generation=cfg.attack_labels_used_in_partition_generation,
        minimum_row_counts=cfg.minimum_row_counts,
        retry_policy=cfg.retry_policy,
        feasibility_failure=cfg.feasibility_failure,
        manifest_invariants=(tuple(cfg.manifest_invariants) if cfg.manifest_invariants is not None else None),
        manifest_fields=(tuple(cfg.manifest_fields) if cfg.manifest_fields is not None else None),
    )


def resolve_adapter_kind(dataset_name: str) -> AdapterKind:
    try:
        return AdapterKind(dataset_name.lower())
    except ValueError as exc:
        raise ConfigurationError(f"Unsupported dataset adapter kind: {dataset_name}") from exc


def resolve_datasets(
    authored_datasets: Sequence,  # Sequence[AuthoredDatasetConfig]
    paths: ResolvedProjectPaths,
) -> dict[DatasetId, ResolvedDataset]:
    """Resolve all authored dataset documents into immutable domain records."""
    resolved: dict[DatasetId, ResolvedDataset] = {}
    for d_cfg in authored_datasets:
        d_id = DatasetId(d_cfg.dataset)
        if d_id in resolved:
            raise ConfigurationError(f"Duplicate dataset identifier across dataset documents: '{d_cfg.dataset}'")
        adapter_kind = resolve_adapter_kind(d_cfg.dataset)
        raw_root = d_cfg.source_layout.root
        dataset_paths = ResolvedDatasetPaths(
            raw_data_root=paths.raw_data,
            raw_root=(paths.raw_data / raw_root).resolve(),
            processed_root=(paths.processed_data / d_cfg.dataset).resolve(),
        )
        setup_identifiers = set(d_cfg.setups)
        setups_list = []
        for identifier, setup in sorted(d_cfg.setups.items()):
            if (
                setup.client_population_must_equal_setup is not None
                and setup.client_population_must_equal_setup not in setup_identifiers
            ):
                raise ConfigurationError(
                    f"Dataset '{d_cfg.dataset}' setup '{identifier}' references unregistered "
                    f"client_population_must_equal_setup '{setup.client_population_must_equal_setup}'"
                )
            setups_list.append(
                DatasetSetup(
                    identifier=DatasetSetupId(identifier),
                    materialization_id=MaterializationId(setup.materialization),
                    capabilities=tuple(setup.provides_capabilities),
                    client_construction=resolve_client_construction(setup.client_construction),
                    validation_scope=setup.validation_scope,
                    eligibility_gate=setup.eligibility_gate,
                    client_population_must_equal_setup=(
                        DatasetSetupId(setup.client_population_must_equal_setup)
                        if setup.client_population_must_equal_setup is not None
                        else None
                    ),
                )
            )
        setups = tuple(setups_list)
        materializations = tuple(
            DatasetMaterialization(
                identifier=MaterializationId(identifier),
                role=materialization.role,
                normalization_strategy=materialization.normalization.strategy,
                normalization_scope=materialization.normalization.scope,
                vocabulary_fit_split=materialization.vocabulary_fit_split,
                preprocessing_sequence=tuple(materialization.preprocessing_sequence),
                row_exclusion=materialization.row_exclusion,
                split_row_semantics=(
                    cast(Mapping[str, "str | bool"], deep_freeze(materialization.split_row_semantics))
                    if materialization.split_row_semantics is not None
                    else None
                ),
                infeasibility_policy=materialization.infeasibility_policy,
                split_method=materialization.split.method,
                split_seed=Seed(materialization.split.split_seed)
                if materialization.split.split_seed is not None
                else None,
                split_ratios=tuple(
                    (role, Probability(ratio)) for role, ratio in sorted((materialization.split.ratios or {}).items())
                ),
                chronological_ratios=tuple(
                    (role, Probability(value))
                    for role, value in (
                        ("historical_train", materialization.split.historical_train_fraction),
                        ("historical_calibration", materialization.split.historical_calibration_fraction),
                        ("future_recalibration", materialization.split.future_recalibration_fraction),
                        ("future_evaluation", materialization.split.future_evaluation_fraction),
                    )
                    if value is not None
                ),
                split_ordering_basis=materialization.split.ordering_basis,
                split_ordering_scope=materialization.split.ordering_scope,
                split_gap_handling=materialization.split.gap_handling,
                split_attack_rows=materialization.split.attack_rows,
                split_attack_test_membership=materialization.split.attack_test_membership,
                split_attack_ordering=materialization.split.attack_ordering,
                split_benign_attack_deduplication=materialization.split.benign_attack_deduplication,
                split_role_order=(
                    tuple(materialization.split.role_order) if materialization.split.role_order is not None else None
                ),
                split_excluded_client_folders=(
                    tuple(materialization.split.excluded_client_folders)
                    if materialization.split.excluded_client_folders is not None
                    else None
                ),
                split_exclusion_reason=materialization.split.exclusion_reason,
                split_ordering_field=materialization.split.ordering_field,
                split_ordering_sort=materialization.split.ordering_sort,
                split_rollover_policy=materialization.split.rollover_policy,
                split_rollover_scope=materialization.split.rollover_scope,
                split_boundary_rule=materialization.split.boundary_rule,
                split_boundary_index_formula=materialization.split.boundary_index_formula,
                split_future_leakage_check=materialization.split.future_leakage_check,
                split_minimum_row_counts=materialization.split.minimum_row_counts,
                split_missing_client_policy=materialization.split.missing_client_policy,
                split_chronology_unverifiable_policy=materialization.split.chronology_unverifiable_policy,
            )
            for identifier, materialization in sorted(d_cfg.materializations.items())
        )
        source_column_count = d_cfg.field_schema.source_column_count
        configured_sources = d_cfg.source_layout.sources
        if d_cfg.field_schema.model_features is not None:
            required_model_headers = tuple(d_cfg.field_schema.model_features.order)
        elif d_cfg.field_schema.retained_numeric_features is not None:
            required_model_headers = tuple(d_cfg.field_schema.retained_numeric_features.order)
        else:
            raise ConfigurationError(f"Dataset '{d_cfg.dataset}' has no resolved model feature headers")
        categorical_encoding = d_cfg.field_schema.categorical_encoding
        required_categorical_headers = (
            tuple(categorical_encoding.columns) if isinstance(categorical_encoding, CategoricalEncodingConfig) else ()
        )
        multiclass_label = d_cfg.field_schema.label_fields.multiclass_label
        label_header = multiclass_label.column if multiclass_label is not None else None
        if configured_sources is None:
            if d_cfg.source_layout.attack_file_pattern is None:
                raise ConfigurationError(
                    f"Dataset '{d_cfg.dataset}' has a single unconfigured source tree "
                    "and must author an explicit 'attack_file_pattern'"
                )
            source_trees = (
                ConfiguredSourceTree(
                    identifier="primary",
                    root=RelativePath(d_cfg.source_layout.root),
                    file_pattern=d_cfg.source_layout.attack_file_pattern,
                    expected_column_count=(
                        source_column_count
                        if isinstance(source_column_count, int)
                        else next(iter(source_column_count.values()))
                    ),
                    executable=True,
                    required_headers=required_model_headers + required_categorical_headers,
                ),
            )
        else:
            source_trees = tuple(
                ConfiguredSourceTree(
                    identifier=identifier,
                    root=RelativePath(source.root),
                    file_pattern=source.file_pattern,
                    expected_column_count=(
                        source_column_count if isinstance(source_column_count, int) else source_column_count[identifier]
                    ),
                    executable=source.role == "executable",
                    required_headers=(
                        required_model_headers
                        + required_categorical_headers
                        + ((label_header,) if source.role == "executable" and label_header is not None else ())
                    ),
                )
                for identifier, source in sorted(configured_sources.items())
            )
        inspection_contract = DatasetInspectionContract(
            source_trees=source_trees,
            require_identical_headers=(
                d_cfg.field_schema.header_must_be_identical_across_all_source_files is True
                or d_cfg.field_schema.header_must_be_identical_across_all_files_in_a_tree is True
            ),
            device_directories=tuple(d_cfg.source_layout.device_dirs or ()),
            benign_filename=d_cfg.source_layout.benign_file,
            benign_file_required_per_device=d_cfg.source_layout.benign_file_required_per_device is True,
            attack_family_directories=tuple(d_cfg.source_layout.attack_family_dirs or ()),
            attack_family_required_per_device=d_cfg.source_layout.attack_family_required_per_device is True,
            normal_group_directories=tuple(d_cfg.source_layout.normal_group_folders or ()),
            attack_filenames=tuple(d_cfg.source_layout.attack_files or ()),
            ignored_root_entries=tuple(d_cfg.source_layout.ignored_root_entries),
            benign_label=(
                str(d_cfg.field_schema.label_fields.binary_label.get("benign_value"))
                if d_cfg.field_schema.label_fields.binary_label is not None
                and isinstance(d_cfg.field_schema.label_fields.binary_label.get("benign_value"), str)
                else None
            ),
            normal_traffic_root=(
                RelativePath(d_cfg.source_layout.normal_traffic_root)
                if d_cfg.source_layout.normal_traffic_root is not None
                else None
            ),
            attack_traffic_root=(
                RelativePath(d_cfg.source_layout.attack_traffic_root)
                if d_cfg.source_layout.attack_traffic_root is not None
                else None
            ),
            binary_label_header=(
                (
                    str(d_cfg.field_schema.label_fields.binary_label["column"])
                    if isinstance(d_cfg.field_schema.label_fields.binary_label.get("column"), str)
                    else None
                )
                if d_cfg.field_schema.label_fields.binary_label is not None
                else None
            ),
        )
        resolved[d_id] = ResolvedDataset(
            dataset_id=d_id,
            adapter_kind=adapter_kind,
            display_name=d_cfg.display_name,
            schema_id=d_cfg.schema_id,
            source_layout=SourceLayout(
                root=RelativePath(d_cfg.source_layout.root),
                ignored_suffixes=tuple(d_cfg.source_layout.ignored_source_suffixes),
                ignored_subtrees=tuple(d_cfg.source_layout.ignored_subtrees),
            ),
            source_layout_contract=resolve_source_layout_contract(d_cfg.source_layout),
            field_schema=resolve_field_schema(d_cfg.field_schema),
            source_contract=resolve_source_contract(d_cfg.source_contract),
            client_identity_contract=(
                as_optional_frozen_json_mapping(d_cfg.client_identity_contract)
                if d_cfg.client_identity_contract is not None
                else None
            ),
            inspection_contract=inspection_contract,
            setups=setups,
            materializations=materializations,
            eligibility_policy_id=EligibilityPolicyId(d_cfg.eligibility_policy),
            capabilities=tuple(sorted({capability for setup in setups for capability in setup.capabilities})),
            paths=dataset_paths,
            fingerprint_source_fields=tuple(d_cfg.fingerprint_inputs.source),
            fingerprint_schema_fields=tuple(d_cfg.fingerprint_inputs.schema_fields),
            fingerprint_materialization_fields=tuple(d_cfg.fingerprint_inputs.materialization),
            fingerprint_client_assignment_fields=tuple(d_cfg.fingerprint_inputs.client_assignment),
        )
    return resolved
