"""Strict contract validation: discriminated unions, enums, and immutable models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp_core.core.identifiers import ClientId, DatasetId, DatasetSetupId, EligibilityPolicyId, MaterializationId
from datp_core.core.numbers import PositiveInt, Probability
from datp_core.core.seeding import Seed
from datp_core.data.contracts.dataset import (
    CICIoT2023Dataset,
    DatasetSetup,
    EdgeIIoTsetDataset,
    MaterializationDefinition,
    NBaIoTDataset,
    ResolvedDatasetPaths,
)
from datp_core.data.contracts.eligibility import EligibilityPolicy, ReadinessGate
from datp_core.data.contracts.enums import (
    MaterializedArtifactShape,
    DatasetPlanKind,
    EncodedFeatureNaming,
    SyntheticClientNamingPolicy,
    ClientIdentityMethod,
    AdapterKind,
    AttackAssignment,
    BoundaryRule,
    CategoryOrder,
    CategoricalEncodingStrategy,
    ChronologyRolloverPolicy,
    ClientConstructionMethod,
    ConstantFeaturePolicy,
    DatasetCapability,
    DeduplicationPolicy,
    DeterministicOrdering,
    GapHandling,
    HashAlgorithm,
    InvalidRowPolicy,
    LabelCasePolicy,
    MissingCategoryPolicy,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
    ParquetCompression,
    SortDirection,
    SourceDiscoveryMode,
    SourceRole,
    SourceTreeKind,
    SplitLayout,
    SplitMembership,
    SplitMethod,
    UnknownCategoryPolicy,
)
from datp_core.data.contracts.materialization import (
    StandardRandomRatios,
    DataLoadingConfig,
    DatasetFileClientConfig,
    DirichletClientConfig,
    DuckDbRuntimeConfig,
    HashConfig,
    OneHotEncodingConfig,
    ParquetWriteConfig,
    PhysicalDeviceClientConfig,
    RandomFractionalSplitConfig,
    SensorGroupClientConfig,
    StandardNormalizationConfig,
    StandardRoleMinimums,
    SyntheticClientNamingConfig,
)
from datp_core.data.contracts.sources import (
    RelativePathClientIdentity,
    CICIoT2023SourceConfig,
    EdgeIIoTsetSourceConfig,
    FileNameClientIdentity,
    NBaIoTSourceConfig,
    SourceInventoryPolicy,
    SourceTreeConfig,
)
from datp_core.core.paths import RelativePath
from datp_core.data.contracts.values import (
    AttackFamilyName,
    CategoryToken,
    ClientNamePrefix,
    ColumnName,
    FeatureName,
    GateId,
    LabelValue,
    SchemaId,
    SourceTreeId,
)
from datp_core.data.materialization.models import (
    CICIoT2023MaterializationPlan,
    EdgeIIoTsetMaterializationPlan,
    MaterializationArtifactLayout,
    NBaIoTDirichletMaterializationPlan,
    NBaIoTPhysicalMaterializationPlan,
    PlanIdentity,
)
from datp_core.core.hashing import Checksum


# ── Strict model: extra fields forbidden ──────────────────────────


def test_strict_model_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetSetup(
            identifier=DatasetSetupId("test"),
            materialization_id=MaterializationId("mat"),
            capabilities=(),
            client_construction=DatasetFileClientConfig(
                method=ClientConstructionMethod.DATASET_FILE_PSEUDO_CLIENTS
            ),
            eligibility_policy_id=EligibilityPolicyId("primary"),
            extra_field="should_fail",
        )


def test_strict_model_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetSetup(
            identifier=DatasetSetupId("test"),
        )


# ── Discriminated union: source configs ──────────────────────────


def test_ciciot2023_source_rejects_invalid_tree_kind() -> None:
    with pytest.raises(ValidationError):
        CICIoT2023SourceConfig(
            adapter=AdapterKind.CICIOT2023,
            tree=SourceTreeConfig(
                identifier=SourceTreeId("primary"),
                kind=SourceTreeKind.DEVICE_HIERARCHY,
                role=SourceRole.EXECUTABLE,
                root=RelativePath("."),
                file_pattern="*.csv",
                discovery=SourceDiscoveryMode.GLOB,
                expected_column_count=3,
                required_headers=(ColumnName("a"), ColumnName("b"), ColumnName("label")),
                headers_must_be_identical=False,
            ),
            inventory=SourceInventoryPolicy(
                ignored_suffixes=(),
                ignored_subtrees=(),
                ignored_root_entries=(),
            ),
            feature_columns=(FeatureName("a"), FeatureName("b")),
            multiclass_label_column=ColumnName("label"),
            benign_label=LabelValue("BENIGN"),
            label_case_policy=LabelCasePolicy.EXACT,
            client_identity=RelativePathClientIdentity(method=ClientIdentityMethod.RELATIVE_PATH_COMPONENT, component_index=0),
            invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
        )


def test_nbaiot_source_requires_fail_source() -> None:
    with pytest.raises(ValidationError):
        NBaIoTSourceConfig(
            adapter=AdapterKind.NBAIOT,
            tree=SourceTreeConfig(
                identifier=SourceTreeId("devices"),
                kind=SourceTreeKind.DEVICE_HIERARCHY,
                role=SourceRole.EXECUTABLE,
                root=RelativePath("."),
                file_pattern="*.csv",
                discovery=SourceDiscoveryMode.RECURSIVE_GLOB,
                expected_column_count=3,
                required_headers=(ColumnName("a"), ColumnName("b")),
                headers_must_be_identical=False,
            ),
            inventory=SourceInventoryPolicy(
                ignored_suffixes=(),
                ignored_subtrees=(),
                ignored_root_entries=(),
            ),
            feature_columns=(FeatureName("a"), FeatureName("b")),
            client_identity=FileNameClientIdentity(method=ClientIdentityMethod.FILE_NAME),
            device_directories=(ClientId("device1"),),
            excluded_device_directories=(),
            benign_filename="benign.csv",
            benign_file_required_per_device=False,
            attack_family_directories=(),
            attack_family_required_per_device=False,
            invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
        )


def test_edge_source_requires_distinct_category_tokens() -> None:
    with pytest.raises(ValidationError):
        EdgeIIoTsetSourceConfig(
            adapter=AdapterKind.EDGE_IIOTSET,
            benign_trees=(),
            attack_reference_trees=(),
            inventory=SourceInventoryPolicy(
                ignored_suffixes=(),
                ignored_subtrees=(),
                ignored_root_entries=(),
            ),
            numeric_columns=(FeatureName("a"),),
            categorical_columns=(),
            binary_label_column=ColumnName("binary"),
            multiclass_label_column=ColumnName("multi"),
            timestamp_column=ColumnName("ts"),
            benign_label=LabelValue("BENIGN"),
            label_case_policy=LabelCasePolicy.EXACT,
            client_identity=FileNameClientIdentity(method=ClientIdentityMethod.FILE_NAME),
            expected_clients=(),
            excluded_clients=(),
            missing_category_token=CategoryToken("MISSING"),
            unknown_category_token=CategoryToken("MISSING"),
            invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
        )


# ── Discriminated union: normalization configs ─────────────────────


def test_standard_normalization_requires_preserve_out_of_range() -> None:
    with pytest.raises(ValidationError):
        StandardNormalizationConfig(
            strategy=NormalizationStrategy.STANDARD,
            fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
            standard_deviation_ddof=0,
            constant_feature_policy=ConstantFeaturePolicy.ZERO,
            out_of_range_policy=OutOfRangePolicy.CLIP,
        )


def test_standard_normalization_validates_ddof() -> None:
    with pytest.raises(ValidationError):
        StandardNormalizationConfig(
            strategy=NormalizationStrategy.STANDARD,
            fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
            standard_deviation_ddof=2,
            constant_feature_policy=ConstantFeaturePolicy.ZERO,
            out_of_range_policy=OutOfRangePolicy.PRESERVE,
        )


def test_standard_normalization_accepts_valid_ddof() -> None:
    cfg = StandardNormalizationConfig(
        strategy=NormalizationStrategy.STANDARD,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        standard_deviation_ddof=0,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.PRESERVE,
    )
    assert cfg.standard_deviation_ddof == 0


# ── Discriminated union: split configs ────────────────────────────


def test_random_split_validates_probability_sum() -> None:
    with pytest.raises(ValidationError):
        RandomFractionalSplitConfig(
            method=SplitMethod.RANDOM_FRACTIONAL,
            seed=Seed(42),
            ratios=StandardRandomRatios(
                layout=SplitLayout.STANDARD,
                train=Probability(0.5),
                calibration=Probability(0.5),
                test=Probability(0.5),
            ),
            attack_assignment=AttackAssignment.TEST,
            deduplication=DeduplicationPolicy.EXACT_WITHIN_CLASS,
            benign_ordering=DeterministicOrdering.CONTENT_DIGEST,
        )


def test_random_split_accepts_valid_ratios() -> None:
    cfg = RandomFractionalSplitConfig(
        method=SplitMethod.RANDOM_FRACTIONAL,
        seed=Seed(42),
        ratios=StandardRandomRatios(
            layout=SplitLayout.STANDARD,
            train=Probability(0.7),
            calibration=Probability(0.15),
            test=Probability(0.15),
        ),
        attack_assignment=AttackAssignment.TEST,
        deduplication=DeduplicationPolicy.EXACT_WITHIN_CLASS,
        benign_ordering=DeterministicOrdering.CONTENT_DIGEST,
    )
    assert cfg.seed == Seed(42)


# ── Discriminated union: client construction ──────────────────────


def test_dirichlet_client_requires_positive_client_count() -> None:
    with pytest.raises(ValidationError):
        DirichletClientConfig(
            method=ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS,
            client_count=0,
            partition_seed=Seed(42),
            seed_key="partition",
            seed_hash=HashConfig(algorithm=HashAlgorithm.BLAKE2B, digest_bytes=8),
            maximum_retries=10,
            minimums=StandardRoleMinimums(
                train=10,
                calibration=10,
                test=10,
            ),
            attack_labels_used_in_partition_generation=False,
            naming=SyntheticClientNamingConfig(
                policy=SyntheticClientNamingPolicy.PREFIXED_ZERO_PADDED_INDEX,
                prefix=ClientNamePrefix("client"),
                first_index=0,
                width=3,
            ),
        )


# ── Discriminated union: categorical encoding ──────────────────────


def test_one_hot_encoding_requires_distinct_indicators() -> None:
    with pytest.raises(ValidationError):
        OneHotEncodingConfig(
            strategy=CategoricalEncodingStrategy.ONE_HOT,
            vocabulary_fit_membership=SplitMembership.TRAIN,
            category_order=CategoryOrder.LEXICOGRAPHIC,
            missing_category_policy=MissingCategoryPolicy.DEDICATED_INDICATOR,
            unknown_category_policy=UnknownCategoryPolicy.DEDICATED_INDICATOR,
            unknown_indicator_distinct_from_missing_indicator=False,
            encoded_feature_naming=EncodedFeatureNaming.COLUMN_EQUALS_CATEGORY,
        )


# ── EligibilityPolicy ──────────────────────────────────────────────


def test_eligibility_policy_validates_positive_minimum() -> None:
    with pytest.raises(ValidationError):
        EligibilityPolicy(
            identifier=EligibilityPolicyId("test"),
            minimum_benign_calibration_count=0,
            require_non_empty_benign_test=True,
            required_attack_capabilities=(),
            exclude_ineligible_clients_from_primary_dispersion=True,
            zero_eligible_clients_is_blocking=True,
        )


def test_eligibility_policy_accepts_valid() -> None:
    policy = EligibilityPolicy(
        identifier=EligibilityPolicyId("primary"),
        minimum_benign_calibration_count=100,
        require_non_empty_benign_test=True,
        required_attack_capabilities=(),
        exclude_ineligible_clients_from_primary_dispersion=True,
        zero_eligible_clients_is_blocking=True,
    )
    assert policy.minimum_benign_calibration_count == 100


# ── ReadinessGate ──────────────────────────────────────────────────


def test_readiness_gate_validates_positive_minimum_clients() -> None:
    with pytest.raises(ValidationError):
        ReadinessGate(
            identifier=GateId("edge_gate"),
            minimum_eligible_clients=0,
            minimum_eligible_proportion=Probability(0.9),
            required_capabilities=(),
        )


def test_readiness_gate_accepts_valid() -> None:
    gate = ReadinessGate(
        identifier=GateId("edge_gate"),
        minimum_eligible_clients=9,
        minimum_eligible_proportion=Probability(0.9),
        required_capabilities=(DatasetCapability.BENIGN_CALIBRATION,),
    )
    assert gate.minimum_eligible_clients == 9


# ── Materialization plan discriminated union ───────────────────────


def test_materialization_plan_kind_literals() -> None:
    plan = CICIoT2023MaterializationPlan(
        kind=DatasetPlanKind.CICIOT2023,
        identity=PlanIdentity(
            dataset_id=DatasetId(DatasetPlanKind.CICIOT2023),
            setup_id=DatasetSetupId("setup"),
            materialization_id=MaterializationId("mat"),
            configuration_checksum=Checksum("a" * 64),
        ),
        adapter=AdapterKind.CICIOT2023,
        source=CICIoT2023SourceConfig(
            adapter=AdapterKind.CICIOT2023,
            tree=SourceTreeConfig(
                identifier=SourceTreeId("primary"),
                kind=SourceTreeKind.MERGED,
                role=SourceRole.EXECUTABLE,
                root=RelativePath("."),
                file_pattern="*.csv",
                discovery=SourceDiscoveryMode.GLOB,
                expected_column_count=3,
                required_headers=(ColumnName("a"), ColumnName("b"), ColumnName("label")),
                headers_must_be_identical=False,
            ),
            inventory=SourceInventoryPolicy(
                ignored_suffixes=(),
                ignored_subtrees=(),
                ignored_root_entries=(),
            ),
            feature_columns=(FeatureName("a"), FeatureName("b")),
            multiclass_label_column=ColumnName("label"),
            benign_label=LabelValue("BENIGN"),
            label_case_policy=LabelCasePolicy.EXACT,
            client_identity=FileNameClientIdentity(method=ClientIdentityMethod.FILE_NAME),
            invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
        ),
        raw_data_root=__import__("pathlib").Path("."),
        split=RandomFractionalSplitConfig(
            method=SplitMethod.RANDOM_FRACTIONAL,
            seed=Seed(42),
            ratios=StandardRandomRatios(
                layout=SplitLayout.STANDARD,
                train=Probability(0.7),
                calibration=Probability(0.15),
                test=Probability(0.15),
            ),
            attack_assignment=AttackAssignment.TEST,
            deduplication=DeduplicationPolicy.EXACT_WITHIN_CLASS,
            benign_ordering=DeterministicOrdering.CONTENT_DIGEST,
        ),
        normalization=StandardNormalizationConfig(
            strategy=NormalizationStrategy.STANDARD,
            fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
            standard_deviation_ddof=0,
            constant_feature_policy=ConstantFeaturePolicy.ZERO,
            out_of_range_policy=OutOfRangePolicy.PRESERVE,
        ),
        client_construction=DatasetFileClientConfig(
            method=ClientConstructionMethod.DATASET_FILE_PSEUDO_CLIENTS
        ),
        eligibility=EligibilityPolicy(
            identifier=EligibilityPolicyId("primary"),
            minimum_benign_calibration_count=100,
            require_non_empty_benign_test=True,
            required_attack_capabilities=(),
            exclude_ineligible_clients_from_primary_dispersion=True,
            zero_eligible_clients_is_blocking=True,
        ),
        readiness_gates=(),
        capabilities=(DatasetCapability.BENIGN_CALIBRATION,),
        expected_client_count=63,
        runtime=DataLoadingConfig(
            chunk_row_count=10000,
            parquet=ParquetWriteConfig(
                compression=ParquetCompression.ZSTD,
                dictionary_encoding=True,
                row_group_size=100000,
                data_page_size=1048576,
            ),
            duckdb=DuckDbRuntimeConfig(
                threads=4,
                memory_limit="4GB",
                preserve_insertion_order=True,
            ),
            row_digest=HashConfig(
                algorithm=HashAlgorithm.BLAKE2B,
                digest_bytes=8,
            ),
        ),
        staging_parent=__import__('pathlib').Path("/tmp"),
        artifact_shape=MaterializedArtifactShape.CICIOT2023,
    )
    assert plan.kind == DatasetPlanKind.CICIOT2023


# ── Enum exhaustiveness ────────────────────────────────────────────


def test_adapter_kind_has_three_members() -> None:
    members = tuple(AdapterKind)
    assert len(members) == 3
    assert AdapterKind.NBAIOT in members
    assert AdapterKind.CICIOT2023 in members
    assert AdapterKind.EDGE_IIOTSET in members


def test_split_membership_has_all_roles() -> None:
    expected = {"train", "calibration", "test", "recalibration_reference",
                "historical_training", "historical_calibration",
                "future_recalibration", "future_evaluation"}
    observed = {m.value for m in SplitMembership}
    assert expected == observed


def test_dataset_capability_has_required_members() -> None:
    required = {"benign_calibration", "attack_evaluation", "temporal_recalibration",
                "physical_client_identity", "pseudo_client_identity",
                "synthetic_client_partition"}
    observed = {m.value for m in DatasetCapability}
    assert required <= observed


# ── Artifact layout ────────────────────────────────────────────────


def test_artifact_layout_derives_paths() -> None:
    layout = MaterializationArtifactLayout.for_staging_root(
        __import__("pathlib").Path("/tmp/staging")
    )
    assert layout.database.name == "materialization.duckdb"
    assert layout.final_payload.name == "dataset.parquet"


# ── Value objects: non-blank validation ────────────────────────────


def test_client_id_rejects_blank() -> None:
    with pytest.raises(ValueError):
        ClientId("")


def test_source_tree_id_rejects_blank() -> None:
    with pytest.raises(ValueError):
        SourceTreeId("  ")


def test_feature_name_rejects_blank() -> None:
    with pytest.raises(ValueError):
        FeatureName("\t")


def test_dataset_id_rejects_path_separators() -> None:
    with pytest.raises(ValueError):
        DatasetId("path/to/dataset")
