"""Source inventory path-containment, filtering, stable ordering, and fingerprint tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import (
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
    ClientId,
)
from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed
from datp_core.data.contracts.dataset import (
    CICIoT2023Dataset,
    ClientFamilyAssignment,
    DatasetSetup,
    MaterializationDefinition,
    ResolvedDatasetPaths,
)
from datp_core.data.contracts.enums import (
    AdapterKind,
    AttackAssignment,
    AuditIssueCode,
    AuditSeverity,
    ClientConstructionMethod,
    ClientIdentityMethod,
    ConstantFeaturePolicy,
    DatasetCapability,
    DeduplicationPolicy,
    DeterministicOrdering,
    InvalidRowPolicy,
    LabelCasePolicy,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
    SourceDiscoveryMode,
    SourceRole,
    SourceTreeKind,
    SplitLayout,
    SplitMethod,
)
from datp_core.data.contracts.materialization import (
    DatasetFileClientConfig,
    MinMaxNormalizationConfig,
    RandomFractionalSplitConfig,
    StandardRandomRatios,
)
from datp_core.data.contracts.sources import (
    CICIoT2023SourceConfig,
    SourceInventoryPolicy,
    SourceTreeConfig,
)
from datp_core.data.contracts.values import (
    ColumnName,
    FeatureName,
    LabelValue,
    SchemaId,
    SourceTreeId,
)
from datp_core.data.readiness.models import SourceAuditReport, SourceTreeAudit
from datp_core.data.readiness.source import assess_source_readiness
from datp_core.data.sources.inventory import (
    build_source_inventory,
    compute_experiment_source_fingerprint,
)
from datp_core.data.sources.models import SourceInventory
from datp_core.core.paths import RelativePath


def _make_source_tree_config(
    root: str,
    identifier: str = "test_tree",
    kind: SourceTreeKind = SourceTreeKind.MERGED,
    role: SourceRole = SourceRole.EXECUTABLE,
    file_pattern: str = "*.csv",
    discovery: SourceDiscoveryMode = SourceDiscoveryMode.GLOB,
    expected_column_count: int = 3,
    headers: tuple[ColumnName, ...] = (ColumnName("feat_a"), ColumnName("feat_b"), ColumnName("label")),
) -> SourceTreeConfig:
    return SourceTreeConfig(
        identifier=SourceTreeId(identifier),
        kind=kind,
        role=role,
        root=RelativePath(root),
        file_pattern=file_pattern,
        discovery=discovery,
        expected_column_count=expected_column_count,
        required_headers=headers,
        headers_must_be_identical=True,
    )


def _make_inventory_policy(
    ignored_suffixes: tuple[str, ...] = (".tmp",),
    ignored_subtrees: tuple[str, ...] = (),
    ignored_root_entries: tuple[str, ...] = (),
) -> SourceInventoryPolicy:
    return SourceInventoryPolicy(
        ignored_suffixes=ignored_suffixes,
        ignored_subtrees=tuple(RelativePath(p) for p in ignored_subtrees),
        ignored_root_entries=ignored_root_entries,
    )


def _make_ciciot2023_source_config(
    tree: SourceTreeConfig,
    policy: SourceInventoryPolicy,
    feature_columns: tuple[str, ...] = ("feat_a", "feat_b"),
    label_column: str = "label",
    benign_label: str = "0",
) -> CICIoT2023SourceConfig:
    return CICIoT2023SourceConfig(
        adapter=AdapterKind.CICIOT2023,
        tree=tree,
        inventory=policy,
        feature_columns=tuple(FeatureName(c) for c in feature_columns),
        multiclass_label_column=ColumnName(label_column),
        benign_label=LabelValue(benign_label),
        label_case_policy=LabelCasePolicy.LOWER,
        client_identity={"method": ClientIdentityMethod.FILE_NAME},
        invalid_row_policy=InvalidRowPolicy.EXCLUDE_ROW,
    )

def _write_csv(path: Path, rows: list[list[str]]) -> None:
    """Write a small CSV file with header row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def _make_minimal_dataset(
    dataset_id: DatasetId,
    raw_data_root: Path,
    source: CICIoT2023SourceConfig,
) -> CICIoT2023Dataset:
    """Build a minimal CICIoT2023Dataset for fingerprint / readiness tests."""
    split_config = RandomFractionalSplitConfig(
        method=SplitMethod.RANDOM_FRACTIONAL,
        seed=Seed(value=42),
        ratios=StandardRandomRatios(
            layout=SplitLayout.STANDARD,
            train=Probability(value=0.7),
            calibration=Probability(value=0.15),
            test=Probability(value=0.15),
        ),
        attack_assignment=AttackAssignment.TEST,
        deduplication=DeduplicationPolicy.NONE,
        benign_ordering=DeterministicOrdering.CONTENT_DIGEST,
    )
    normalization_config = MinMaxNormalizationConfig(
        strategy=NormalizationStrategy.MIN_MAX,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        constant_feature_policy=ConstantFeaturePolicy.ERROR,
        out_of_range_policy=OutOfRangePolicy.ERROR,
    )

    return CICIoT2023Dataset(
        adapter=AdapterKind.CICIOT2023,
        dataset_id=dataset_id,
        display_name=dataset_id.value,
        schema_id=SchemaId(f"{dataset_id.value}_v1"),
        source=source,
        paths=ResolvedDatasetPaths(
            raw_data_root=raw_data_root,
            processed_root=raw_data_root / "processed",
        ),
        capabilities=(DatasetCapability.BENIGN_CALIBRATION, DatasetCapability.ATTACK_EVALUATION),
        setups=(
            DatasetSetup(
                identifier=DatasetSetupId("default"),
                materialization_id=MaterializationId("default"),
                capabilities=(DatasetCapability.BENIGN_CALIBRATION,),
                client_construction=DatasetFileClientConfig(
                    method=ClientConstructionMethod.DATASET_FILE_PSEUDO_CLIENTS
                ),
                eligibility_policy_id=EligibilityPolicyId("default"),
            ),
        ),
        materializations=(
            MaterializationDefinition(
                identifier=MaterializationId("default"),
                split=split_config,
                normalization=normalization_config,
            ),
        ),
        family_assignments=(
            ClientFamilyAssignment(client_id=ClientId("device_1"), family="benign"),
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildSourceInventory:
    """Tests for build_source_inventory() with temp CSV fixtures."""

    def test_includes_all_csv_files(self) -> None:
        """Inventory discovers every CSV file in the source-tree root."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device_1.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])
            _write_csv(root / "device_2.csv", [["feat_a", "feat_b", "label"], ["3.0", "4.0", "1"]])
            _write_csv(root / "device_3.csv", [["feat_a", "feat_b", "label"], ["5.0", "6.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy()
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            assert isinstance(inventory, SourceInventory)
            assert inventory.file_count == 3
            assert len(inventory.entries) == 3

    def test_filters_ignored_suffixes(self) -> None:
        """Files with ignored suffixes are excluded from the inventory."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "good.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])
            _write_csv(root / "skip.tmp", [["feat_a", "feat_b", "label"], ["3.0", "4.0", "1"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=(".tmp",))
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            assert inventory.file_count == 1
            assert inventory.entries[0].source_path.name == "good.csv"

    def test_stable_ordering_by_tree_id_then_relative_path(self) -> None:
        """Inventory entries are sorted by source_tree_id then relative path."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "z_file.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])
            _write_csv(root / "a_file.csv", [["feat_a", "feat_b", "label"], ["3.0", "4.0", "1"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            paths = [entry.relative_path.as_posix() for entry in inventory.entries]
            assert paths == sorted(paths)

    def test_no_duplicate_paths(self) -> None:
        """Inventory must not contain duplicate entries."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            resolved = {str(entry.source_path) for entry in inventory.entries}
            assert len(resolved) == inventory.file_count

    def test_all_entries_are_within_raw_data_root(self) -> None:
        """Every inventory entry is contained within raw_data_root."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            resolved_root = root.resolve()
            for entry in inventory.entries:
                assert entry.source_path.is_relative_to(resolved_root)

    def test_each_entry_carries_source_tree_id(self) -> None:
        """Every entry has the correct source-tree identifier."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".", identifier="ciciot2023_tree")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            for entry in inventory.entries:
                assert entry.source_tree_id == SourceTreeId("ciciot2023_tree")
                assert entry.tree_kind is SourceTreeKind.MERGED
                assert entry.role is SourceRole.EXECUTABLE

    def test_checksum_changes_when_file_content_changes(self) -> None:
        """Modifying a source file produces a different inventory checksum."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "device.csv"
            _write_csv(csv_path, [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            first = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            _write_csv(csv_path, [["feat_a", "feat_b", "label"], ["9.9", "8.8", "1"]])

            second = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            assert first.checksum != second.checksum

    def test_checksum_stable_for_identical_sources(self) -> None:
        """Rebuilding the inventory without changes yields the same checksum."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            first = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )
            second = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            assert first.checksum == second.checksum

    def test_all_entries_point_to_existing_files(self) -> None:
        """Every discovered path exists and is a regular file."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )

            for entry in inventory.entries:
                assert entry.source_path.exists()
                assert entry.source_path.is_file()


class TestComputeExperimentSourceFingerprint:
    """Tests for compute_experiment_source_fingerprint dict-based API."""

    def test_fingerprint_is_deterministic(self) -> None:
        """Same datasets produce the same experiment fingerprint."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)
            ds_id = DatasetId("test")
            dataset = _make_minimal_dataset(ds_id, root, source)
            datasets: dict[DatasetId, CICIoT2023Dataset] = {ds_id: dataset}

            fp1 = compute_experiment_source_fingerprint(datasets=datasets, dataset_ids=(ds_id,))
            fp2 = compute_experiment_source_fingerprint(datasets=datasets, dataset_ids=(ds_id,))

            assert isinstance(fp1, Checksum)
            assert fp1 == fp2

    def test_fingerprint_differs_with_different_content(self) -> None:
        """Different source content produces a different fingerprint."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])
            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)
            ds_id = DatasetId("test")
            dataset = _make_minimal_dataset(ds_id, root, source)

            fp_first = compute_experiment_source_fingerprint(
                datasets={ds_id: dataset}, dataset_ids=(ds_id,)
            )

            # Replace file content
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["9.9", "8.8", "1"]])
            # Rebuild dataset with new raw_data_root — same dir, content changed
            dataset2 = _make_minimal_dataset(ds_id, root, source)

            fp_second = compute_experiment_source_fingerprint(
                datasets={ds_id: dataset2}, dataset_ids=(ds_id,)
            )

            assert fp_first != fp_second

    def test_multiple_datasets_change_fingerprint(self) -> None:
        """Including an additional dataset changes the combined fingerprint."""
        with TemporaryDirectory() as tmp_a, TemporaryDirectory() as tmp_b:
            root_a = Path(tmp_a)
            root_b = Path(tmp_b)
            _write_csv(root_a / "a.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])
            _write_csv(root_b / "b.csv", [["feat_a", "feat_b", "label"], ["3.0", "4.0", "1"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            ds_a_id = DatasetId("ds_a")
            ds_b_id = DatasetId("ds_b")
            ds_a = _make_minimal_dataset(ds_a_id, root_a, source)
            ds_b = _make_minimal_dataset(ds_b_id, root_b, source)
            datasets: dict[DatasetId, CICIoT2023Dataset] = {ds_a_id: ds_a, ds_b_id: ds_b}

            fp_single = compute_experiment_source_fingerprint(
                datasets=datasets, dataset_ids=(ds_a_id,)
            )
            fp_both = compute_experiment_source_fingerprint(
                datasets=datasets, dataset_ids=(ds_a_id, ds_b_id)
            )

            assert fp_single != fp_both


class TestAssessSourceReadiness:
    """Tests for assess_source_readiness returning typed reports."""

    def test_returns_source_audit_report_type(self) -> None:
        """assess_source_readiness returns a SourceAuditReport."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )
            report = assess_source_readiness(source, inventory)

            assert isinstance(report, SourceAuditReport)
            assert isinstance(report.tree_audits, tuple)
            assert isinstance(report.issues, tuple)

    def test_blocking_issues_when_tree_has_no_files(self) -> None:
        """An empty source tree produces a BLOCKING issue."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            # No CSV files at all
            tree = _make_source_tree_config(root="data")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )
            report = assess_source_readiness(source, inventory)

            blocking = report.blocking_issues
            assert len(blocking) >= 1
            assert any(issue.code is AuditIssueCode.NO_SOURCE_FILES for issue in blocking)
            assert all(issue.severity is AuditSeverity.BLOCKING for issue in blocking)

    def test_tree_audit_contains_executable_flag(self) -> None:
        """Tree audit records the executable flag correctly."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "device.csv", [["feat_a", "feat_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )
            report = assess_source_readiness(source, inventory)

            for audit in report.tree_audits:
                assert isinstance(audit, SourceTreeAudit)
                assert audit.executable is True
                assert audit.file_count >= 1

    def test_header_mismatch_raises_blocking_issue(self) -> None:
        """A CSV with wrong headers produces a blocking issue."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(root / "bad.csv", [["wrong_a", "wrong_b", "label"], ["1.0", "2.0", "0"]])

            tree = _make_source_tree_config(root=".")
            policy = _make_inventory_policy(ignored_suffixes=())
            source = _make_ciciot2023_source_config(tree, policy)

            inventory = build_source_inventory(
                dataset_id=DatasetId("test"),
                raw_data_root=root,
                source=source,
            )
            report = assess_source_readiness(source, inventory)

            blocking = report.blocking_issues
            assert any(issue.code is AuditIssueCode.SOURCE_HEADER_MISMATCH for issue in blocking)
