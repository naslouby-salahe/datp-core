from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from re import fullmatch

from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage

_MANIFEST_FILENAME = "MANIFEST_SHA256.csv"
_SIDECAR_FILENAME = "MANIFEST_SHA256.sha256"
_ROADMAP_LOCK_FILENAME = "ROADMAP_LOCK.md"
_REQUIRED_DIRECTORIES = (
    "DATA_PROVENANCE",
    "SPLIT_IDENTITY",
    "PREPROCESSING",
    "MODELS",
    "SCORES",
    "THRESHOLDS",
    "METRICS",
    "STATISTICS",
    "FIGURE_TABLE_DATA",
    "AUDIT_REPORTS",
    "ENVIRONMENT",
)
_REQUIRED_FILES = (
    _ROADMAP_LOCK_FILENAME,
    _MANIFEST_FILENAME,
    _SIDECAR_FILENAME,
    "SEEDS.csv",
    "README_REPRODUCIBILITY.md",
)
_MANIFEST_COLUMNS = (
    "relative_path",
    "sha256",
    "bytes",
    "artifact_type",
    "dataset_id",
    "population_id",
    "training_method",
    "training_seed",
    "threshold_policy",
    "experiment_id",
)


@dataclass(frozen=True, slots=True)
class ReleaseManifestEntry:
    relative_path: Path
    digest: str
    byte_count: int
    artifact_type: str
    dataset_id: str
    population_id: str
    training_method: str
    training_seed: str
    threshold_policy: str
    experiment_id: str


@dataclass(frozen=True, slots=True)
class ReleaseValidation:
    root: Path
    entries: tuple[ReleaseManifestEntry, ...]


def validate_release_bundle(root: Path) -> ReleaseValidation:
    """Validate the complete released-byte inventory required for reconstruction."""

    _require_payload_layout(root)
    manifest_path = root / _MANIFEST_FILENAME
    _validate_manifest_sidecar(manifest_path, root / _SIDECAR_FILENAME)
    entries = _read_manifest(manifest_path)
    _validate_manifest_files(root, entries)
    return ReleaseValidation(root=root, entries=entries)


def _require_payload_layout(root: Path) -> None:
    missing = tuple(name for name in _REQUIRED_FILES if not (root / name).is_file())
    missing_directories = tuple(name for name in _REQUIRED_DIRECTORIES if not (root / name).is_dir())
    if missing or missing_directories:
        raise ArtifactIntegrityError(
            ErrorMessage(
                "release bundle payload is incomplete: "
                f"files={','.join(missing) or 'none'}; directories={','.join(missing_directories) or 'none'}"
            )
        )


def _validate_manifest_sidecar(manifest_path: Path, sidecar_path: Path) -> None:
    expected = f"{_sha256_file(manifest_path)}  {_MANIFEST_FILENAME}\n"
    actual = sidecar_path.read_text(encoding="utf-8")
    if actual != expected:
        raise ArtifactIntegrityError(ErrorMessage("release manifest sidecar does not match the exact manifest bytes"))


def _read_manifest(path: Path) -> tuple[ReleaseManifestEntry, ...]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or tuple(reader.fieldnames) != _MANIFEST_COLUMNS:
            raise ArtifactIntegrityError(ErrorMessage("release manifest columns do not match the locked schema"))
        entries = tuple(_manifest_entry(row) for row in reader)
    if not entries:
        raise ArtifactIntegrityError(ErrorMessage("release manifest must list released artifacts"))
    paths = tuple(entry.relative_path for entry in entries)
    if len(paths) != len(frozenset(paths)):
        raise ArtifactIntegrityError(ErrorMessage("release manifest repeats an artifact path"))
    return entries


def _manifest_entry(row: dict[str, str | None]) -> ReleaseManifestEntry:
    values = tuple(row.get(column) for column in _MANIFEST_COLUMNS)
    if any(value is None or value == "" for value in values):
        raise ArtifactIntegrityError(ErrorMessage("release manifest fields must use explicit values or NA"))
    relative_path = Path(_required_value(row, "relative_path"))
    if relative_path.is_absolute() or ".." in relative_path.parts or relative_path.name in {
        _MANIFEST_FILENAME,
        _SIDECAR_FILENAME,
    }:
        raise ArtifactIntegrityError(ErrorMessage("release manifest contains an invalid artifact path"))
    digest = _required_value(row, "sha256")
    if fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ArtifactIntegrityError(ErrorMessage("release manifest requires lowercase SHA-256 digests"))
    try:
        byte_count = int(_required_value(row, "bytes"))
    except ValueError as error:
        raise ArtifactIntegrityError(ErrorMessage("release manifest byte count must be an integer")) from error
    if byte_count < 0:
        raise ArtifactIntegrityError(ErrorMessage("release manifest byte count must be non-negative"))
    return ReleaseManifestEntry(
        relative_path=relative_path,
        digest=digest,
        byte_count=byte_count,
        artifact_type=_required_value(row, "artifact_type"),
        dataset_id=_required_value(row, "dataset_id"),
        population_id=_required_value(row, "population_id"),
        training_method=_required_value(row, "training_method"),
        training_seed=_required_value(row, "training_seed"),
        threshold_policy=_required_value(row, "threshold_policy"),
        experiment_id=_required_value(row, "experiment_id"),
    )


def _required_value(row: dict[str, str | None], column: str) -> str:
    value = row.get(column)
    if value is None or value == "":
        raise ArtifactIntegrityError(ErrorMessage(f"release manifest field is missing: {column}"))
    return value


def _validate_manifest_files(root: Path, entries: tuple[ReleaseManifestEntry, ...]) -> None:
    listed = frozenset(entry.relative_path for entry in entries)
    actual = frozenset(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and path.name not in {_MANIFEST_FILENAME, _SIDECAR_FILENAME}
    )
    if listed != actual:
        raise ArtifactIntegrityError(
            ErrorMessage(
                "release manifest inventory mismatch: "
                f"missing={','.join(str(path) for path in sorted(actual - listed)) or 'none'}; "
                f"unexpected={','.join(str(path) for path in sorted(listed - actual)) or 'none'}"
            )
        )
    for entry in entries:
        path = root / entry.relative_path
        if path.stat().st_size != entry.byte_count:
            raise ArtifactIntegrityError(ErrorMessage(f"release artifact byte count mismatch: {entry.relative_path}"))
        if _sha256_file(path) != entry.digest:
            raise ArtifactIntegrityError(ErrorMessage(f"release artifact digest mismatch: {entry.relative_path}"))


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
