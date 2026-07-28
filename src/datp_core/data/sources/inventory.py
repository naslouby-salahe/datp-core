"""Deterministic source discovery and fingerprinting."""

from __future__ import annotations

from pathlib import Path

from datp_core.core.hashing import Checksum, compute_file_checksum, compute_payload_checksum
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.contracts.enums import DataFailureCode, SourceDiscoveryMode
from datp_core.data.contracts.sources import DatasetSourceConfig, SourceInventoryPolicy, SourceTreeConfig
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.sources.models import SourceEntry, SourceInventory


def build_source_inventory(
    dataset_id: DatasetId,
    raw_data_root: Path,
    source: DatasetSourceConfig,
) -> SourceInventory:
    resolved_root = raw_data_root.resolve()
    entries: list[SourceEntry] = []
    for tree in _source_trees(source):
        tree_root = (resolved_root / tree.root.value).resolve()
        _require_contained(tree_root, resolved_root)
        for path in _discover(tree_root, tree, source.inventory):
            resolved_path = path.resolve()
            _require_contained(resolved_path, tree_root)
            entries.append(
                SourceEntry(
                    source_path=resolved_path,
                    relative_path=resolved_path.relative_to(resolved_root),
                    source_tree_id=tree.identifier,
                    tree_kind=tree.kind,
                    role=tree.role,
                )
            )
    ordered = tuple(sorted(entries, key=lambda entry: (entry.source_tree_id.value, entry.relative_path.as_posix())))
    payload = "\n".join(
        f"{entry.source_tree_id.value}:{entry.role.value}:{entry.relative_path.as_posix()}:"
        f"{compute_file_checksum(entry.source_path).value}"
        for entry in ordered
    ).encode("utf-8")
    return SourceInventory(
        dataset_id=dataset_id,
        raw_data_root=resolved_root,
        entries=ordered,
        checksum=compute_payload_checksum(payload),
    )


def _source_trees(source: DatasetSourceConfig) -> tuple[SourceTreeConfig, ...]:
    from datp_core.data.contracts.sources import CICIoT2023SourceConfig, EdgeIIoTsetSourceConfig, NBaIoTSourceConfig

    if isinstance(source, CICIoT2023SourceConfig | NBaIoTSourceConfig):
        return (source.tree,)
    if isinstance(source, EdgeIIoTsetSourceConfig):
        return source.benign_trees + source.attack_reference_trees
    raise DataFailure(
        DataFailureCode.CONFIGURATION,
        "unsupported dataset source contract",
        source_path=None,
        source_row_index=None,
    )


def _discover(
    tree_root: Path,
    tree: SourceTreeConfig,
    policy: SourceInventoryPolicy,
) -> tuple[Path, ...]:
    if not tree_root.is_dir():
        return ()
    candidates = (
        tree_root.glob(tree.file_pattern)
        if tree.discovery is SourceDiscoveryMode.GLOB
        else tree_root.rglob(tree.file_pattern)
    )
    ignored_subtrees = tuple((tree_root / path.value).resolve() for path in policy.ignored_subtrees)
    ignored_suffixes = tuple(suffix.casefold() for suffix in policy.ignored_suffixes)
    selected: list[Path] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        if candidate.suffix.casefold() in ignored_suffixes:
            continue
        if candidate.name in policy.ignored_root_entries and candidate.parent == tree_root:
            continue
        resolved = candidate.resolve()
        if any(resolved.is_relative_to(subtree) for subtree in ignored_subtrees):
            continue
        selected.append(candidate)
    return tuple(sorted(selected, key=lambda path: path.relative_to(tree_root).as_posix()))


def _require_contained(path: Path, root: Path) -> None:
    if not path.is_relative_to(root):
        raise DataFailure(
            DataFailureCode.SOURCE_CONTAINMENT,
            f"path escapes configured root '{root.as_posix()}'",
            source_path=path,
            source_row_index=None,
        )


def compute_experiment_source_fingerprint(
    *,
    datasets: dict[DatasetId, ResolvedDataset],
    dataset_ids: tuple[DatasetId, ...],
) -> Checksum:
    parts: list[str] = []
    for dataset_id in sorted(dataset_ids, key=lambda d: d.value):
        dataset = datasets[dataset_id]
        inventory = build_source_inventory(dataset_id, dataset.paths.raw_data_root, dataset.source)
        parts.append(f"{dataset_id.value}:{inventory.checksum.value}")
    payload = "\n".join(parts).encode("utf-8")
    return compute_payload_checksum(payload)
