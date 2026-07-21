"""Deterministic executable source inventory for materialization and provenance.

Applies configured source-tree resolution, path containment, glob semantics,
ignored suffixes/subtrees, required directory layout, stable relative-path
ordering, and duplicate-path detection exactly once.
"""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.domain.datasets import ConfiguredSourceTree, DatasetInspectionContract, ResolvedDataset
from datp_core.domain.fingerprints import Checksum, compute_file_checksum, compute_payload_checksum
from datp_core.domain.identifiers import DatasetId


@define(frozen=True, slots=True, kw_only=True)
class ConcreteSourceEntry:
    """One ordered, typed source file with provenance."""

    source_path: Path
    relative_path: Path
    source_tree_identifier: str


@define(frozen=True, slots=True, kw_only=True)
class ConcreteSourceInventory:
    """Deterministic, ordered source-file inventory for one resolved dataset."""

    dataset_id: DatasetId
    entries: tuple[ConcreteSourceEntry, ...]

    @property
    def file_count(self) -> int:
        return len(self.entries)

    def fingerprint(self) -> Checksum:
        """Fingerprint the ordered source bytes together with their configured paths."""
        payload = "\n".join(
            f"{entry.relative_path.as_posix()}:{compute_file_checksum(entry.source_path).value}"
            for entry in self.entries
        ).encode("utf-8")
        return compute_payload_checksum(payload)


def build_source_inventory(dataset: ResolvedDataset) -> ConcreteSourceInventory:
    """Build the sole ordered source inventory for a resolved dataset.

    Materializers and source fingerprinting consume this inventory; audit
    retains non-executable source trees as configured inspection evidence.
    """
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

    # Stable ordering: sort by relative path for deterministic iteration order.
    all_entries.sort(key=lambda entry: entry.relative_path.as_posix())

    return ConcreteSourceInventory(
        dataset_id=dataset.dataset_id,
        entries=tuple(all_entries),
    )


def _inventory_source_tree(
    source_root: Path,
    tree: ConfiguredSourceTree,
    ignored_suffixes: frozenset[str],
    ignored_subtrees: tuple[Path, ...],
    inspection: DatasetInspectionContract,
) -> list[Path]:
    """Collect matching files from one configured source tree, applying all filtering rules.

    Uses the exact same glob/rglob logic as the dataset audit's _source_files method:
    rglob("*.csv") when device_directories or normal_group_directories are present,
    otherwise glob(tree.file_pattern).
    """
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
        # Apply ignored suffixes from the source layout
        if path.suffix.lower() in ignored_suffixes:
            continue
        # Apply ignored subtrees (resolved absolute paths from source_layout.ignored_subtrees)
        if any(path.is_relative_to(ignored) for ignored in ignored_subtrees):
            continue
        filtered.append(path)

    # Sort by relative path for determinism.
    filtered.sort(key=lambda p: p.relative_to(source_root).as_posix())
    return filtered
