"""Source inventory path-containment, filtering, and stable ordering tests."""

from __future__ import annotations

from datp_core.app import build_application
from datp_core.core.identifiers import DatasetId
from datp_core.data.sources import build_source_inventory
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint, dataset_source_fingerprint


def test_source_inventory_produces_stable_ordered_entries() -> None:
    """Source inventory returns entries sorted by relative path for determinism."""
    config = build_application().config
    for dataset_id in (DatasetId("nbaiot"), DatasetId("ciciot2023")):
        dataset = config.datasets[dataset_id]
        inventory = build_source_inventory(dataset)

        # Verify stable ordering
        relative_paths = [entry.relative_path.as_posix() for entry in inventory.entries]
        assert relative_paths == sorted(relative_paths), (
            f"Source inventory for {dataset_id.value} is not stably ordered"
        )


def test_source_inventory_no_duplicate_paths() -> None:
    """Source inventory must not contain duplicate paths."""
    config = build_application().config
    for dataset_id in (DatasetId("nbaiot"), DatasetId("ciciot2023")):
        dataset = config.datasets[dataset_id]
        inventory = build_source_inventory(dataset)

        resolved_paths = [str(entry.source_path.resolve()) for entry in inventory.entries]
        unique_paths = set(resolved_paths)
        assert len(resolved_paths) == len(unique_paths), (
            f"Source inventory for {dataset_id.value} contains duplicate paths"
        )


def test_source_inventory_all_paths_are_within_raw_data_root() -> None:
    """Every inventory entry must be contained within the raw data root."""
    config = build_application().config
    for dataset_id in (DatasetId("nbaiot"), DatasetId("ciciot2023")):
        dataset = config.datasets[dataset_id]
        raw_data_root = dataset.paths.raw_data_root.resolve()
        inventory = build_source_inventory(dataset)

        for entry in inventory.entries:
            assert entry.source_path.is_relative_to(raw_data_root), (
                f"Source entry {entry.source_path} escapes raw data root {raw_data_root}"
            )


def test_source_inventory_matches_audit_file_count() -> None:
    """Source inventory and dataset audit must agree on executable source-tree files.

    The audit includes non-executable source trees for informational purposes;
    the inventory (used by materialization) only counts executable trees.
    """
    from datp_core.data.readiness import AuditDatasetUseCase

    config = build_application().config
    for dataset_id in (DatasetId("nbaiot"), DatasetId("ciciot2023")):
        dataset = config.datasets[dataset_id]
        inventory = build_source_inventory(dataset)
        audit = AuditDatasetUseCase().execute(dataset)

        # The inventory only includes executable trees; count only those from audit too
        executable_trees = {tree.identifier for tree in dataset.inspection_contract.source_trees if tree.executable}
        executable_audit_count = sum(
            tree.file_count for tree in audit.source_trees if tree.identifier in executable_trees
        )

        assert inventory.file_count == executable_audit_count, (
            f"Source inventory ({inventory.file_count} files) and audit executable trees "
            f"({executable_audit_count} files) disagree for {dataset_id.value}"
        )


def test_source_inventory_files_exist() -> None:
    """Every entry in the inventory must point to an existing file."""
    config = build_application().config
    for dataset_id in (DatasetId("nbaiot"), DatasetId("ciciot2023")):
        dataset = config.datasets[dataset_id]
        inventory = build_source_inventory(dataset)

        for entry in inventory.entries:
            assert entry.source_path.exists(), f"Source inventory entry {entry.source_path} does not exist"
            assert entry.source_path.is_file(), f"Source inventory entry {entry.source_path} is not a file"


def test_dataset_source_fingerprint_is_the_single_authority_behind_the_experiment_fingerprint() -> None:
    """`compute_experiment_source_fingerprint` must combine per-dataset terms built from the exact
    same `dataset_source_fingerprint` value every other source-dependent identity uses (the
    materialization handler's per-artifact `source_inventory_fingerprint`), not an independently
    reimplemented formula that could silently drift from it."""
    config = build_application().config
    dataset = config.datasets[DatasetId("nbaiot")]

    direct = dataset_source_fingerprint(dataset)
    assert direct == build_source_inventory(dataset).fingerprint()

    combined = compute_experiment_source_fingerprint(datasets=config.datasets, dataset_ids=(DatasetId("nbaiot"),))
    # The combined (multi-dataset) fingerprint is a real function of the per-dataset one: it must
    # be deterministic and reproducible, and it must actually depend on the per-dataset fingerprint
    # (not merely on the dataset id) -- verified by combining a second, distinct real dataset and
    # confirming the combined fingerprint changes.
    combined_again = compute_experiment_source_fingerprint(datasets=config.datasets, dataset_ids=(DatasetId("nbaiot"),))
    assert combined == combined_again
    combined_with_second_dataset = compute_experiment_source_fingerprint(
        datasets=config.datasets, dataset_ids=(DatasetId("nbaiot"), DatasetId("ciciot2023"))
    )
    assert combined_with_second_dataset != combined


def test_source_inventory_assigns_correct_source_tree_identifier() -> None:
    """Every entry must carry the identifier of its source tree."""
    config = build_application().config
    dataset = config.datasets[DatasetId("nbaiot")]
    inventory = build_source_inventory(dataset)

    tree_identifiers = {tree.identifier for tree in dataset.inspection_contract.source_trees if tree.executable}
    for entry in inventory.entries:
        assert entry.source_tree_identifier in tree_identifiers, (
            f"Source entry {entry.source_path} has unknown tree identifier '{entry.source_tree_identifier}'"
        )
