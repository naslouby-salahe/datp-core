"""Deterministic source inventory discovery — one shared authority."""

from __future__ import annotations

from pathlib import Path

from datp_core.core.hashing import Checksum, compute_payload_checksum
from datp_core.core.identifiers import DatasetId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.contracts.sources import ConfiguredSourceTree, DatasetInspectionContract
from datp_core.data.sources.models import ConcreteSourceEntry, ConcreteSourceInventory


def build_source_inventory(dataset: ResolvedDataset) -> ConcreteSourceInventory:
    raw_data_root = dataset.paths.raw_data_root.resolve()
    inspection = dataset.inspection_contract
    ignored_suffixes = frozenset(s.lower() for s in dataset.source_layout.ignored_suffixes)
    ignored_subtrees = tuple(
        (raw_data_root / relative_path).resolve() for relative_path in dataset.source_layout.ignored_subtrees
    )

    all_entries: list[ConcreteSourceEntry] = []
    seen_paths: set[Path] = set()

    for tree in inspection.source_trees:
        if not tree.executable:
            continue
        source_root = (raw_data_root / tree.root.value).resolve()
        if not source_root.is_dir():
            continue
        if not source_root.is_relative_to(raw_data_root):
            continue

        files = _inventory_source_tree(source_root, tree, ignored_suffixes, ignored_subtrees, inspection)
        for file_path in files:
            resolved = file_path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            all_entries.append(
                ConcreteSourceEntry(
                    source_path=resolved,
                    relative_path=resolved.relative_to(raw_data_root),
                    source_tree_identifier=tree.identifier,
                )
            )

    all_entries.sort(key=lambda entry: entry.relative_path.as_posix())

    return ConcreteSourceInventory(
        dataset_id=dataset.dataset_id,
        entries=tuple(all_entries),
    )


def dataset_source_fingerprint(dataset: ResolvedDataset) -> Checksum:
    """The single authoritative source-provenance fingerprint for one dataset: a BLAKE2b checksum
    over its sorted, ignore-filtered source inventory. Every source-dependent identity in this
    codebase -- a materialized artifact's ``source_inventory_fingerprint`` and each per-dataset
    term inside ``compute_experiment_source_fingerprint`` -- must derive from this one function
    rather than independently calling ``build_source_inventory(dataset).fingerprint()``, so the
    two can never silently drift into different formulas over the same underlying files.
    """
    return build_source_inventory(dataset).fingerprint()


def compute_experiment_source_fingerprint(
    *, datasets: TypedDomainRegistry[DatasetId, ResolvedDataset], dataset_ids: tuple[DatasetId, ...]
) -> Checksum:
    """Compute a deterministic combined source-provenance fingerprint for an experiment.

    Builds a source inventory for every dataset the experiment depends on and returns
    a BLAKE2b checksum over the concatenation of all per-dataset inventory fingerprints.
    This fingerprint changes when any raw source file content, path, or membership changes.
    """
    parts: list[str] = []
    for dataset_id in sorted(dataset_ids, key=lambda d: d.value):
        dataset = datasets[dataset_id]
        parts.append(f"{dataset_id.value}:{dataset_source_fingerprint(dataset).value}")
    payload = "\n".join(parts).encode("utf-8")
    return compute_payload_checksum(payload)


def _inventory_source_tree(
    source_root: Path,
    tree: ConfiguredSourceTree,
    ignored_suffixes: frozenset[str],
    ignored_subtrees: tuple[Path, ...],
    inspection: DatasetInspectionContract,
) -> list[Path]:
    if inspection.device_directories or inspection.normal_group_directories:
        candidates = source_root.rglob("*.csv")
    else:
        pattern = tree.file_pattern
        if "**" in pattern:
            candidates = source_root.rglob(pattern)
        else:
            candidates = source_root.glob(pattern)

    filtered: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix.lower() in ignored_suffixes:
            continue
        if any(path.is_relative_to(ignored) for ignored in ignored_subtrees):
            continue
        filtered.append(path)

    filtered.sort(key=lambda p: p.relative_to(source_root).as_posix())
    return filtered
