"""Dataset-resolution functions extracted from the monolithic resolver.

Ownership boundary: converts authored dataset Pydantic models into immutable
domain records owned by ``data/contracts/dataset.py``. Exports a narrow function surface;
does not import pipeline execution, CLI, or infrastructure.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from datp_core.config.authored.datasets import (
    AuthoredDatasetConfig,
    CategoricalEncodingConfig,
    MaterializationConfig,
    SetupClientConstructionConfig,
    SetupConfig,
    SplitSpecConfig,
)
from datp_core.config.errors import ConfigurationError
from datp_core.config.resolution.runtime import ResolvedProjectPaths
from datp_core.core.identifiers import (
    ClientId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
)
from datp_core.core.numbers import Probability
from datp_core.core.paths import RelativePath
from datp_core.core.seeding import Seed
from datp_core.data.contracts.dataset import (
    CICIoT2023Dataset,
    ClientFamilyAssignment,
    DatasetSetup,
    EdgeIIoTsetDataset,
    EdgeMaterializationDefinition,
    MaterializationDefinition,
    NBaIoTDataset,
    ResolvedDataset,
    ResolvedDatasetPaths,
)
from datp_core.data.contracts.enums import (
    AdapterKind,
    AttackAssignment,
    BoundaryRule,
    CategoricalEncodingStrategy,
    CategoryOrder,
    ChronologyRolloverPolicy,
    ClientConstructionMethod,
    ClientIdentityMethod,
    ConstantFeaturePolicy,
    DatasetCapability,
    DeduplicationPolicy,
    DeterministicOrdering,
    EncodedFeatureNaming,
    GapHandling,
    HashAlgorithm,
    InvalidRowPolicy,
    LabelCasePolicy,
    MissingCategoryPolicy,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
    SortDirection,
    SourceDiscoveryMode,
    SourceRole,
    SourceTreeKind,
    SplitLayout,
    SplitMembership,
    SplitMethod,
    SyntheticClientNamingPolicy,
    UnknownCategoryPolicy,
)
from datp_core.data.contracts.materialization import (
    ChronologicalGappedRatios,
    ChronologicalGappedSplitConfig,
    ClientConstructionConfig,
    DatasetFileClientConfig,
    DirichletClientConfig,
    HashConfig,
    MinMaxNormalizationConfig,
    NormalizationConfig,
    OneHotEncodingConfig,
    PhysicalDeviceClientConfig,
    RandomFractionalSplitConfig,
    SensorGroupClientConfig,
    SplitConfig,
    StandardNormalizationConfig,
    StandardRandomRatios,
    StandardRoleMinimums,
    StaticReferenceRandomRatios,
    SyntheticClientNamingConfig,
    TemporalRatios,
    TemporalRoleMinimums,
    WithinClientChronologicalSplitConfig,
)
from datp_core.data.contracts.sources import (
    CICIoT2023SourceConfig,
    EdgeIIoTsetSourceConfig,
    FileNameClientIdentity,
    NBaIoTSourceConfig,
    RelativePathClientIdentity,
    SourceInventoryPolicy,
    SourceTreeConfig,
)
from datp_core.data.contracts.values import (
    AttackFamilyName,
    CategoryToken,
    ClientNamePrefix,
    ColumnName,
    FeatureName,
    LabelValue,
    SchemaId,
    SourceTreeId,
)

# ---------------------------------------------------------------------------
# Source config builders
# ---------------------------------------------------------------------------


def _build_inventory_policy(d_cfg: AuthoredDatasetConfig) -> SourceInventoryPolicy:
    """Build a SourceInventoryPolicy from the authored source_layout."""
    layout = d_cfg.source_layout
    return SourceInventoryPolicy(
        ignored_suffixes=tuple(layout.ignored_source_suffixes),
        ignored_subtrees=tuple(RelativePath(p) for p in layout.ignored_subtrees),
        ignored_root_entries=tuple(layout.ignored_root_entries),
    )


def _ciciot2023_required_headers(d_cfg: AuthoredDatasetConfig) -> tuple[ColumnName, ...]:
    """Build required column headers for CICIoT2023: model features + Label."""
    features = d_cfg.field_schema.model_features
    if features is None:
        raise ConfigurationError("CICIoT2023 dataset must define model_features")
    headers = [ColumnName(name) for name in features.order]
    multiclass = d_cfg.field_schema.label_fields.multiclass_label
    if multiclass is not None:
        headers.append(ColumnName(multiclass.column))
    return tuple(headers)


def _nbaiot_required_headers(d_cfg: AuthoredDatasetConfig) -> tuple[ColumnName, ...]:
    """Build required column headers for N-BaIoT: exactly the model features."""
    features = d_cfg.field_schema.model_features
    if features is None:
        raise ConfigurationError("N-BaIoT dataset must define model_features")
    return tuple(ColumnName(name) for name in features.order)


def _edge_required_headers(d_cfg: AuthoredDatasetConfig) -> tuple[ColumnName, ...]:
    """Build required column headers for Edge-IIoTset.

    Includes retained numeric features, categorical encoding columns, and label columns.
    """
    retained = d_cfg.field_schema.retained_numeric_features
    encoding = d_cfg.field_schema.categorical_encoding
    headers: list[ColumnName] = []
    if retained is not None:
        headers.extend(ColumnName(name) for name in retained.order)
    if isinstance(encoding, CategoricalEncodingConfig):
        headers.extend(ColumnName(name) for name in encoding.columns)
    label_fields = d_cfg.field_schema.label_fields
    binary_label = label_fields.binary_label
    multiclass_label = label_fields.multiclass_label
    if isinstance(binary_label, dict) and "column" in binary_label:
        headers.append(ColumnName(str(binary_label["column"])))
    if multiclass_label is not None:
        headers.append(ColumnName(multiclass_label.column))
    return tuple(headers)


def _headers_must_be_identical(d_cfg: AuthoredDatasetConfig) -> bool:
    field = d_cfg.field_schema
    return bool(
        field.header_must_be_identical_across_all_source_files
        or field.header_must_be_identical_across_all_files_in_a_tree
    )


def _build_ciciot2023_source(d_cfg: AuthoredDatasetConfig) -> CICIoT2023SourceConfig:
    """Build the CICIoT2023 source config from the authored document."""
    field = d_cfg.field_schema
    features = field.model_features
    if features is None:
        raise ConfigurationError("CICIoT2023 requires model_features")
    multiclass = field.label_fields.multiclass_label
    if multiclass is None:
        raise ConfigurationError("CICIoT2023 requires a multiclass label definition")

    source = d_cfg.source_layout.sources
    if source is None or "merged" not in source:
        raise ConfigurationError("CICIoT2023 requires a 'merged' source definition")
    merged = source["merged"]
    source_column_count = field.source_column_count
    expected_count = (
        source_column_count["merged"]
        if isinstance(source_column_count, dict)
        else source_column_count
    )

    tree = SourceTreeConfig(
        identifier=SourceTreeId("merged"),
        kind=SourceTreeKind.MERGED,
        role=SourceRole.EXECUTABLE,
        root=RelativePath(merged.root),
        file_pattern=merged.file_pattern,
        discovery=SourceDiscoveryMode.GLOB,
        expected_column_count=expected_count,
        required_headers=_ciciot2023_required_headers(d_cfg),
        headers_must_be_identical=_headers_must_be_identical(d_cfg),
    )

    benign_label_str = str(
        field.label_fields.binary_label.get("benign_value", "BENIGN")
        if isinstance(field.label_fields.binary_label, dict)
        else "BENIGN"
    )

    label_case_str = multiclass.case or "exact"
    case_policy: LabelCasePolicy
    if label_case_str == "upper":
        case_policy = LabelCasePolicy.UPPER
    elif label_case_str == "lower":
        case_policy = LabelCasePolicy.LOWER
    elif label_case_str == "casefold":
        case_policy = LabelCasePolicy.CASEFOLD
    else:
        case_policy = LabelCasePolicy.EXACT

    return CICIoT2023SourceConfig(
        adapter=AdapterKind.CICIOT2023,
        tree=tree,
        inventory=_build_inventory_policy(d_cfg),
        feature_columns=tuple(FeatureName(name) for name in features.order),
        multiclass_label_column=ColumnName(multiclass.column),
        benign_label=LabelValue(benign_label_str),
        label_case_policy=case_policy,
        client_identity=FileNameClientIdentity(method=ClientIdentityMethod.FILE_NAME),
        invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
    )


def _build_nbaiot_source(d_cfg: AuthoredDatasetConfig) -> NBaIoTSourceConfig:
    """Build the N-BaIoT source config from the authored document."""
    field = d_cfg.field_schema
    features = field.model_features
    if features is None:
        raise ConfigurationError("N-BaIoT requires model_features")
    layout = d_cfg.source_layout

    source_column_count = field.source_column_count
    expected_count = (
        next(iter(source_column_count.values()))
        if isinstance(source_column_count, dict)
        else source_column_count
    )

    tree = SourceTreeConfig(
        identifier=SourceTreeId("primary"),
        kind=SourceTreeKind.DEVICE_HIERARCHY,
        role=SourceRole.EXECUTABLE,
        root=RelativePath(layout.root),
        file_pattern="*.csv",
        discovery=SourceDiscoveryMode.RECURSIVE_GLOB,
        expected_column_count=expected_count,
        required_headers=_nbaiot_required_headers(d_cfg),
        headers_must_be_identical=_headers_must_be_identical(d_cfg),
    )

    return NBaIoTSourceConfig(
        adapter=AdapterKind.NBAIOT,
        tree=tree,
        inventory=_build_inventory_policy(d_cfg),
        feature_columns=tuple(FeatureName(name) for name in features.order),
        client_identity=RelativePathClientIdentity(
            method=ClientIdentityMethod.RELATIVE_PATH_COMPONENT,
            component_index=0,
        ),
        device_directories=tuple(ClientId(d) for d in (layout.device_dirs or ())),
        excluded_device_directories=(),
        benign_filename=layout.benign_file or "benign_traffic.csv",
        benign_file_required_per_device=bool(layout.benign_file_required_per_device),
        attack_family_directories=tuple(
            AttackFamilyName(d) for d in (layout.attack_family_dirs or ())
        ),
        attack_family_required_per_device=bool(layout.attack_family_required_per_device),
        invalid_row_policy=InvalidRowPolicy.FAIL_SOURCE,
    )


def _build_edge_iiotset_source(d_cfg: AuthoredDatasetConfig) -> EdgeIIoTsetSourceConfig:
    """Build the Edge-IIoTset source config from the authored document."""
    field = d_cfg.field_schema
    layout = d_cfg.source_layout

    source_column_count = field.source_column_count
    expected_count = (
        next(iter(source_column_count.values()))
        if isinstance(source_column_count, dict)
        else source_column_count
    )

    headers = _edge_required_headers(d_cfg)
    headers_must_be_identical = _headers_must_be_identical(d_cfg)

    groups = tuple(layout.executable_group_folders or layout.normal_group_folders or ())

    benign_trees = tuple(
        SourceTreeConfig(
            identifier=SourceTreeId(group),
            kind=SourceTreeKind.BENIGN_GROUPS,
            role=SourceRole.EXECUTABLE,
            root=RelativePath(f"{layout.normal_traffic_root}/{group}"),
            file_pattern="*.csv",
            discovery=SourceDiscoveryMode.GLOB,
            expected_column_count=expected_count,
            required_headers=headers,
            headers_must_be_identical=headers_must_be_identical,
        )
        for group in groups
    )

    if layout.attack_traffic_root is not None:
        attack_reference_trees = (
            SourceTreeConfig(
                identifier=SourceTreeId("attack_reference"),
                kind=SourceTreeKind.ATTACK_REFERENCE,
                role=SourceRole.AUDIT_ONLY,
                root=RelativePath(layout.attack_traffic_root),
                file_pattern=layout.attack_file_pattern or "*_attack.csv",
                discovery=SourceDiscoveryMode.GLOB,
                expected_column_count=expected_count,
                required_headers=headers,
                headers_must_be_identical=headers_must_be_identical,
            ),
        )
    else:
        attack_reference_trees = ()

    binary_label = field.label_fields.binary_label
    binary_label_column = (
        str(binary_label.get("column", "Attack_label"))
        if isinstance(binary_label, dict)
        else "Attack_label"
    )
    benign_value_dict = field.label_fields.benign_value or {}
    benign_label_str = (
        str(benign_value_dict.get("Attack_label", "0"))
        if isinstance(benign_value_dict, dict)
        else "0"
    )
    multiclass_label = field.label_fields.multiclass_label
    timestamp_field = field.identity_scheme.timestamp_field
    timestamp_column = (
        timestamp_field.get("column", "frame.time")
        if isinstance(timestamp_field, dict)
        else timestamp_field
    )

    encoding = field.categorical_encoding
    if not isinstance(encoding, CategoricalEncodingConfig):
        raise ConfigurationError("Edge-IIoTset requires a categorical encoding configuration")

    numeric_columns = (
        tuple(FeatureName(name) for name in field.retained_numeric_features.order)
        if field.retained_numeric_features is not None
        else ()
    )

    return EdgeIIoTsetSourceConfig(
        adapter=AdapterKind.EDGE_IIOTSET,
        benign_trees=benign_trees,
        attack_reference_trees=attack_reference_trees,
        inventory=_build_inventory_policy(d_cfg),
        numeric_columns=numeric_columns,
        categorical_columns=tuple(ColumnName(name) for name in encoding.columns),
        binary_label_column=ColumnName(binary_label_column),
        multiclass_label_column=(
            ColumnName(multiclass_label.column)
            if multiclass_label is not None
            else ColumnName("Attack_type")
        ),
        timestamp_column=ColumnName(str(timestamp_column)),
        benign_label=LabelValue(benign_label_str),
        label_case_policy=LabelCasePolicy.EXACT,
        client_identity=RelativePathClientIdentity(
            method=ClientIdentityMethod.RELATIVE_PATH_COMPONENT,
            component_index=0,
        ),
        expected_clients=tuple(ClientId(g) for g in groups),
        excluded_clients=(),
        missing_category_token=CategoryToken("<missing>"),
        unknown_category_token=CategoryToken("<unknown>"),
        invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
    )


# ---------------------------------------------------------------------------
# Split config builders
# ---------------------------------------------------------------------------


def _parse_attack_assignment(split: SplitSpecConfig) -> AttackAssignment:
    """Map authored split attack_rows/attack_test_membership to AttackAssignment."""
    if split.attack_rows and "evaluation" in split.attack_rows:
        return AttackAssignment.TEST
    return AttackAssignment.EXCLUDE


def _parse_deduplication(split: SplitSpecConfig) -> DeduplicationPolicy:
    """Map authored deduplication to DeduplicationPolicy."""
    dedup = split.benign_attack_deduplication
    if dedup is None:
        return DeduplicationPolicy.NONE
    if "not_applied" in dedup or "retain" in dedup:
        return DeduplicationPolicy.NONE
    if "exact" in dedup and "class" in dedup.lower():
        return DeduplicationPolicy.EXACT_WITHIN_CLASS
    if "exact" in dedup:
        return DeduplicationPolicy.EXACT_WITHIN_CLIENT
    return DeduplicationPolicy.NONE


def _parse_benign_ordering(split: SplitSpecConfig) -> DeterministicOrdering:
    """Map authored ordering_basis to DeterministicOrdering."""
    basis = split.ordering_basis
    if basis and "source_row" in basis:
        return DeterministicOrdering.SOURCE_PROVENANCE
    return DeterministicOrdering.CONTENT_DIGEST


def _parse_sort_direction(split: SplitSpecConfig) -> SortDirection:
    """Map authored ordering_sort to SortDirection."""
    ordering = split.ordering_sort or ""
    if "descending" in ordering or "desc" in ordering:
        return SortDirection.DESCENDING
    return SortDirection.ASCENDING


def _build_random_fractional_split(split: SplitSpecConfig) -> RandomFractionalSplitConfig:
    """Build a RandomFractionalSplitConfig from authored split config."""
    ratios_raw = split.ratios or {}
    has_recalibration = "recalibration_reference" in ratios_raw

    if has_recalibration:
        ratios = StaticReferenceRandomRatios(
            layout=SplitLayout.STATIC_RECALIBRATION_REFERENCE,
            train=Probability(ratios_raw.get("train", 0.7)),
            calibration=Probability(ratios_raw.get("calibration", 0.15)),
            recalibration_reference=Probability(ratios_raw.get("recalibration_reference", 0.10)),
            test=Probability(ratios_raw.get("test", 0.15)),
        )
    else:
        ratios = StandardRandomRatios(
            layout=SplitLayout.STANDARD,
            train=Probability(ratios_raw.get("train", 0.7)),
            calibration=Probability(ratios_raw.get("calibration", 0.15)),
            test=Probability(ratios_raw.get("test", 0.15)),
        )

    return RandomFractionalSplitConfig(
        method=SplitMethod.RANDOM_FRACTIONAL,
        seed=Seed(split.split_seed) if split.split_seed is not None else Seed(0),
        ratios=ratios,
        attack_assignment=_parse_attack_assignment(split),
        deduplication=_parse_deduplication(split),
        benign_ordering=_parse_benign_ordering(split),
    )


def _build_chronological_gapped_split(split: SplitSpecConfig) -> ChronologicalGappedSplitConfig:
    """Build a ChronologicalGappedSplitConfig from authored split config."""
    ratios_raw = split.ratios or {}
    ratios = ChronologicalGappedRatios(
        train=Probability(ratios_raw.get("train", 0.60)),
        first_gap=Probability(ratios_raw.get("gap_1", 0.01)),
        calibration=Probability(ratios_raw.get("calibration", 0.20)),
        second_gap=Probability(ratios_raw.get("gap_2", 0.01)),
        test=Probability(ratios_raw.get("test", 0.18)),
    )
    return ChronologicalGappedSplitConfig(
        method=SplitMethod.CHRONOLOGICAL_GAPPED,
        ratios=ratios,
        attack_assignment=_parse_attack_assignment(split),
        gap_handling=GapHandling.EXCLUDE,
        boundary_rule=BoundaryRule.FLOOR,
        sort_direction=_parse_sort_direction(split),
    )


def _build_within_client_chronological_split(
    split: SplitSpecConfig,
) -> WithinClientChronologicalSplitConfig:
    """Build a WithinClientChronologicalSplitConfig from authored split config."""
    ratios = TemporalRatios(
        historical_training=Probability(split.historical_train_fraction or 0.55),
        historical_calibration=Probability(split.historical_calibration_fraction or 0.15),
        future_recalibration=Probability(split.future_recalibration_fraction or 0.10),
        future_evaluation=Probability(split.future_evaluation_fraction or 0.20),
    )
    min_counts = split.minimum_row_counts or {}
    minimums = TemporalRoleMinimums(
        historical_training=min_counts.get("historical_train", 100),
        historical_calibration=min_counts.get("historical_calibration", 100),
        future_recalibration=min_counts.get("future_recalibration", 50),
        future_evaluation=min_counts.get("future_evaluation", 100),
    )
    return WithinClientChronologicalSplitConfig(
        method=SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL,
        ratios=ratios,
        minimums=minimums,
        attack_assignment=_parse_attack_assignment(split),
        sort_direction=_parse_sort_direction(split),
        rollover_policy=ChronologyRolloverPolicy.ADD_FIXED_PERIOD_ON_DECREASE,
        rollover_period_seconds=86400,
        boundary_rule=BoundaryRule.FLOOR,
    )


def _build_split_config(split: SplitSpecConfig) -> SplitConfig:
    """Build the discriminated SplitConfig from an authored SplitSpecConfig."""
    method = split.method
    if method == "random_fractional":
        return _build_random_fractional_split(split)
    if method == "chronological_gapped":
        return _build_chronological_gapped_split(split)
    if method == "within_client_chronological":
        return _build_within_client_chronological_split(split)
    raise ConfigurationError(f"Unsupported split method: {method}")


# ---------------------------------------------------------------------------
# Normalization config builders
# ---------------------------------------------------------------------------


def _build_normalization_config(mat_cfg: MaterializationConfig) -> NormalizationConfig:
    """Build the discriminated NormalizationConfig from an authored MaterializationConfig."""
    norm = mat_cfg.normalization
    strategy = norm.strategy
    scope_str = norm.scope

    fit_scope: NormalizationFitScope
    if scope_str == "global_train":
        fit_scope = NormalizationFitScope.GLOBAL_TRAIN
    elif scope_str == "per_client_train":
        fit_scope = NormalizationFitScope.PER_CLIENT_TRAIN
    elif scope_str == "historical_train":
        fit_scope = NormalizationFitScope.HISTORICAL_TRAIN
    else:
        raise ConfigurationError(f"Unsupported normalization scope: {scope_str}")

    if strategy == "min_max":
        return MinMaxNormalizationConfig(
            strategy=NormalizationStrategy.MIN_MAX,
            fit_scope=fit_scope,
            constant_feature_policy=ConstantFeaturePolicy.ZERO,
            out_of_range_policy=OutOfRangePolicy.CLIP,
        )
    if strategy == "standard":
        return StandardNormalizationConfig(
            strategy=NormalizationStrategy.STANDARD,
            fit_scope=fit_scope,
            standard_deviation_ddof=1,
            constant_feature_policy=ConstantFeaturePolicy.ZERO,
            out_of_range_policy=OutOfRangePolicy.PRESERVE,
        )
    raise ConfigurationError(f"Unsupported normalization strategy: {strategy}")


# ---------------------------------------------------------------------------
# One-hot encoding config builder
# ---------------------------------------------------------------------------


def _build_one_hot_encoding_config(
    mat_cfg: MaterializationConfig,
    d_cfg: AuthoredDatasetConfig,
) -> OneHotEncodingConfig:
    """Build OneHotEncodingConfig from materialization and dataset config."""
    encoding = d_cfg.field_schema.categorical_encoding
    if not isinstance(encoding, CategoricalEncodingConfig):
        raise ConfigurationError("Edge-IIoTset requires a categorical encoding configuration")

    vocab_split = mat_cfg.vocabulary_fit_split or "benign_train"
    if "historical" in vocab_split:
        vocab_membership = SplitMembership.HISTORICAL_TRAINING
    else:
        vocab_membership = SplitMembership.TRAIN

    return OneHotEncodingConfig(
        strategy=CategoricalEncodingStrategy.ONE_HOT,
        vocabulary_fit_membership=vocab_membership,
        category_order=CategoryOrder.LEXICOGRAPHIC,
        missing_category_policy=MissingCategoryPolicy.DEDICATED_INDICATOR,
        unknown_category_policy=UnknownCategoryPolicy.DEDICATED_INDICATOR,
        unknown_indicator_distinct_from_missing_indicator=True,
        encoded_feature_naming=EncodedFeatureNaming.COLUMN_EQUALS_CATEGORY,
    )


# ---------------------------------------------------------------------------
# Client construction config builder
# ---------------------------------------------------------------------------


def _build_client_construction_config(
    cfg: SetupClientConstructionConfig,
) -> ClientConstructionConfig:
    """Build the discriminated ClientConstructionConfig from authored config."""
    method = cfg.method

    if method == "dataset_file_pseudo_clients":
        return DatasetFileClientConfig(
            method=ClientConstructionMethod.DATASET_FILE_PSEUDO_CLIENTS,
        )

    if method == "physical_device_clients":
        return PhysicalDeviceClientConfig(
            method=ClientConstructionMethod.PHYSICAL_DEVICE_CLIENTS,
        )

    if method == "sensor_group_clients":
        return SensorGroupClientConfig(
            method=ClientConstructionMethod.SENSOR_GROUP_CLIENTS,
        )

    if method == "dirichlet_partitioned_clients":
        retry_policy = cfg.retry_policy or {}
        min_rows = cfg.minimum_row_counts or {}
        max_retries = retry_policy.get("max_retries", 10) if isinstance(retry_policy, dict) else 10
        return DirichletClientConfig(
            method=ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS,
            client_count=cfg.client_count or 20,
            partition_seed=Seed(cfg.partition_seed) if cfg.partition_seed is not None else Seed(0),
            seed_key="dirichlet",
            seed_hash=HashConfig(algorithm=HashAlgorithm.BLAKE2B, digest_bytes=8),
            maximum_retries=int(max_retries),
            minimums=StandardRoleMinimums(
                train=min_rows.get("train", 100),
                calibration=min_rows.get("calibration", 100),
                test=min_rows.get("test", 50),
            ),
            attack_labels_used_in_partition_generation=False,
            naming=SyntheticClientNamingConfig(
                policy=SyntheticClientNamingPolicy.PREFIXED_ZERO_PADDED_INDEX,
                prefix=ClientNamePrefix("client"),
                first_index=0,
                width=3,
            ),
        )

    raise ConfigurationError(f"Unsupported client construction method: {method}")


# ---------------------------------------------------------------------------
# Capability resolver
# ---------------------------------------------------------------------------


def _resolve_capabilities(setup_cfg: SetupConfig) -> tuple[DatasetCapability, ...]:
    """Map authored capabilities to DatasetCapability enums.

    Only capabilities that directly correspond to a DatasetCapability are
    included. Additional implied capabilities are derived from the client
    construction method.
    """
    capabilities: set[DatasetCapability] = set()
    for cap in setup_cfg.provides_capabilities:
        if cap == "benign_calibration":
            capabilities.add(DatasetCapability.BENIGN_CALIBRATION)
        elif cap in (
            "benign_test_false_positive_metrics",
            "per_client_attack_detection_metrics",
            "attack_sensitive_threshold_tradeoff",
        ):
            capabilities.add(DatasetCapability.ATTACK_EVALUATION)
        elif cap == "within_client_chronological_ordering":
            capabilities.add(DatasetCapability.TEMPORAL_RECALIBRATION)

    method = setup_cfg.client_construction.method
    if method == "physical_device_clients":
        capabilities.add(DatasetCapability.PHYSICAL_CLIENT_IDENTITY)
    elif method == "dataset_file_pseudo_clients":
        capabilities.add(DatasetCapability.PSEUDO_CLIENT_IDENTITY)
    elif method in ("dirichlet_partitioned_clients",):
        capabilities.add(DatasetCapability.SYNTHETIC_CLIENT_PARTITION)

    return tuple(sorted(capabilities, key=lambda c: c.value))


# ---------------------------------------------------------------------------
# Setup and materialization resolvers
# ---------------------------------------------------------------------------


def _resolve_family_assignments(
    d_cfg: AuthoredDatasetConfig,
) -> tuple[ClientFamilyAssignment, ...]:
    """Build family assignments from the authored family_map if present."""
    family_map = d_cfg.field_schema.label_fields.family_map
    if family_map is None:
        return ()
    return tuple(
        ClientFamilyAssignment(client_id=ClientId(device), family=str(family))
        for device, family in family_map.items()
    )


def _resolve_setups(
    d_cfg: AuthoredDatasetConfig,
) -> tuple[DatasetSetup, ...]:
    """Resolve authored setups into DatasetSetup domain records."""
    return tuple(
        DatasetSetup(
            identifier=DatasetSetupId(identifier),
            materialization_id=MaterializationId(setup_cfg.materialization),
            capabilities=_resolve_capabilities(setup_cfg),
            client_construction=_build_client_construction_config(setup_cfg.client_construction),
            eligibility_policy_id=EligibilityPolicyId(
                setup_cfg.eligibility_gate or d_cfg.eligibility_policy
            ),
        )
        for identifier, setup_cfg in sorted(d_cfg.setups.items())
    )


def _resolve_materializations(
    d_cfg: AuthoredDatasetConfig,
) -> tuple[MaterializationDefinition, ...]:
    """Resolve authored materializations into MaterializationDefinition domain records."""
    results: list[MaterializationDefinition] = []

    for _identifier, mat_cfg in sorted(d_cfg.materializations.items()):
        split = _build_split_config(mat_cfg.split)
        normalization = _build_normalization_config(mat_cfg)
        results.append(
            MaterializationDefinition(
                identifier=MaterializationId(mat_cfg.materialization_id),
                split=split,
                normalization=normalization,
            )
        )

    return tuple(results)


def _resolve_edge_materializations(
    d_cfg: AuthoredDatasetConfig,
) -> tuple[EdgeMaterializationDefinition, ...]:
    """Resolve authored materializations into EdgeMaterializationDefinition records."""
    results: list[EdgeMaterializationDefinition] = []

    for _identifier, mat_cfg in sorted(d_cfg.materializations.items()):
        split = _build_split_config(mat_cfg.split)
        normalization = _build_normalization_config(mat_cfg)
        encoding = _build_one_hot_encoding_config(mat_cfg, d_cfg)
        results.append(
            EdgeMaterializationDefinition(
                identifier=MaterializationId(mat_cfg.materialization_id),
                split=split,
                normalization=normalization,
                categorical_encoding=encoding,
            )
        )

    return tuple(results)


# ---------------------------------------------------------------------------
# Adapter kind resolver
# ---------------------------------------------------------------------------


def resolve_adapter_kind(dataset_name: str) -> AdapterKind:
    """Resolve the dataset adapter kind from the canonical dataset name."""
    try:
        return AdapterKind(dataset_name.lower())
    except ValueError as exc:
        raise ConfigurationError(f"Unsupported dataset adapter kind: {dataset_name}") from exc


# ---------------------------------------------------------------------------
# Source config dispatch
# ---------------------------------------------------------------------------


def _build_source_config(
    d_cfg: AuthoredDatasetConfig,
    adapter_kind: AdapterKind,
) -> CICIoT2023SourceConfig | NBaIoTSourceConfig | EdgeIIoTsetSourceConfig:
    """Dispatch source config construction based on the adapter kind."""
    if adapter_kind is AdapterKind.CICIOT2023:
        return _build_ciciot2023_source(d_cfg)
    if adapter_kind is AdapterKind.NBAIOT:
        return _build_nbaiot_source(d_cfg)
    if adapter_kind is AdapterKind.EDGE_IIOTSET:
        return _build_edge_iiotset_source(d_cfg)
    raise ConfigurationError(f"Unsupported adapter kind: {adapter_kind}")


# ---------------------------------------------------------------------------
# Dataset constructor helpers
# ---------------------------------------------------------------------------


def _build_single_dataset(
    d_id: DatasetId,
    d_cfg: AuthoredDatasetConfig,
    adapter_kind: AdapterKind,
    source: CICIoT2023SourceConfig | NBaIoTSourceConfig | EdgeIIoTsetSourceConfig,
    paths: ResolvedProjectPaths,
) -> ResolvedDataset:
    """Build one typed dataset record from resolved components."""
    dataset_paths = ResolvedDatasetPaths(
        raw_data_root=paths.raw_data,
        processed_root=(paths.processed_data / d_cfg.dataset).resolve(),
    )
    setups = _resolve_setups(d_cfg)
    family_assignments = _resolve_family_assignments(d_cfg)

    capabilities = tuple(
        sorted(
            {capability for setup in setups for capability in setup.capabilities},
            key=lambda c: c.value,
        )
    )

    schema_id = SchemaId(d_cfg.schema_id)

    if adapter_kind is AdapterKind.CICIOT2023:
        materializations = _resolve_materializations(d_cfg)
        return CICIoT2023Dataset(
            adapter=AdapterKind.CICIOT2023,
            dataset_id=d_id,
            display_name=d_cfg.display_name,
            schema_id=schema_id,
            source=cast(CICIoT2023SourceConfig, source),
            paths=dataset_paths,
            capabilities=capabilities,
            setups=setups,
            materializations=materializations,
            family_assignments=family_assignments,
        )
    if adapter_kind is AdapterKind.NBAIOT:
        materializations = _resolve_materializations(d_cfg)
        return NBaIoTDataset(
            adapter=AdapterKind.NBAIOT,
            dataset_id=d_id,
            display_name=d_cfg.display_name,
            schema_id=schema_id,
            source=cast(NBaIoTSourceConfig, source),
            paths=dataset_paths,
            capabilities=capabilities,
            setups=setups,
            materializations=materializations,
            family_assignments=family_assignments,
        )
    if adapter_kind is AdapterKind.EDGE_IIOTSET:
        edge_materializations = _resolve_edge_materializations(d_cfg)
        return EdgeIIoTsetDataset(
            adapter=AdapterKind.EDGE_IIOTSET,
            dataset_id=d_id,
            display_name=d_cfg.display_name,
            schema_id=schema_id,
            source=cast(EdgeIIoTsetSourceConfig, source),
            paths=dataset_paths,
            capabilities=capabilities,
            setups=setups,
            materializations=edge_materializations,
            family_assignments=family_assignments,
        )
    raise ConfigurationError(f"Unsupported adapter kind: {adapter_kind}")


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------


def resolve_datasets(
    authored_datasets: Sequence[AuthoredDatasetConfig],
    paths: ResolvedProjectPaths,
) -> dict[DatasetId, ResolvedDataset]:
    """Resolve all authored dataset documents into immutable domain records.

    Returns a mapping from DatasetId to one of the discriminated dataset
    types: CICIoT2023Dataset, NBaIoTDataset, or EdgeIIoTsetDataset.
    """
    resolved: dict[DatasetId, ResolvedDataset] = {}
    for d_cfg in authored_datasets:
        d_id = DatasetId(d_cfg.dataset)
        if d_id in resolved:
            raise ConfigurationError(
                f"Duplicate dataset identifier across dataset documents: '{d_cfg.dataset}'"
            )
        adapter_kind = resolve_adapter_kind(d_cfg.dataset)
        source = _build_source_config(d_cfg, adapter_kind)
        resolved[d_id] = _build_single_dataset(d_id, d_cfg, adapter_kind, source, paths)
    return resolved
