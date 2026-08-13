from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from platform import platform, processor
from re import fullmatch
from shutil import copy2
from sys import version

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


class ReleaseState(StrEnum):
    PUBLIC = "PUBLIC"
    BLINDED_ARCHIVE = "BLINDED_ARCHIVE"
    WITHHELD_LICENSE_RESTRICTED = "WITHHELD_LICENSE_RESTRICTED"


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    source: Path
    relative_path: Path
    artifact_type: str
    dataset_id: str = "NA"
    population_id: str = "NA"
    training_method: str = "NA"
    training_seed: str = "NA"
    threshold_policy: str = "NA"
    experiment_id: str = "NA"


@dataclass(frozen=True, slots=True)
class ReleaseBuildRequest:
    root: Path
    roadmap: Path
    code_revision: str
    literature_search_date: date
    state: ReleaseState
    confirmatory_seeds: tuple[int, ...]
    artifacts: tuple[ReleaseArtifact, ...]


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


def build_release_bundle(request: ReleaseBuildRequest) -> ReleaseValidation:
    """Build a release only from explicit retained artifacts, then validate its exact byte inventory."""

    if request.root.exists():
        raise ArtifactIntegrityError(ErrorMessage("release destination must not already exist"))
    if not request.roadmap.is_file():
        raise ArtifactIntegrityError(ErrorMessage("release roadmap snapshot is missing"))
    if len(request.confirmatory_seeds) != 10 or len(set(request.confirmatory_seeds)) != 10:
        raise ArtifactIntegrityError(ErrorMessage("release requires the exact ten unique confirmatory seeds"))
    _require_unique_release_artifacts(request.artifacts)
    request.root.mkdir(parents=True)
    for directory in _REQUIRED_DIRECTORIES:
        (request.root / directory).mkdir()
    _write_release_metadata(request)
    for artifact in request.artifacts:
        _copy_release_artifact(request.root, artifact)
    _write_manifest(request.root, request.artifacts)
    return validate_release_bundle(request.root)


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


def _require_unique_release_artifacts(artifacts: tuple[ReleaseArtifact, ...]) -> None:
    paths = tuple(item.relative_path for item in artifacts)
    if len(paths) != len(frozenset(paths)):
        raise ArtifactIntegrityError(ErrorMessage("release artifact destinations must be unique"))
    for artifact in artifacts:
        if not artifact.source.is_file():
            raise ArtifactIntegrityError(ErrorMessage(f"release source artifact is missing: {artifact.source}"))
        _require_relative_artifact_path(artifact.relative_path)


def _write_release_metadata(request: ReleaseBuildRequest) -> None:
    roadmap_digest = _sha256_file(request.roadmap)
    (request.root / _ROADMAP_LOCK_FILENAME).write_text(
        "# DATP-Core roadmap lock\n\n"
        f"- Roadmap SHA-256: `{roadmap_digest}`\n"
        f"- Code revision: `{request.code_revision}`\n"
        f"- Literature search date: `{request.literature_search_date.isoformat()}`\n"
        f"- Release state: `{request.state.value}`\n\n"
        "## Exact roadmap snapshot\n\n"
        + request.roadmap.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (request.root / "SEEDS.csv").write_text(
        "training_seed,purpose,derivation\n"
        + "".join(
            f"{seed},confirmatory_training,declared_confirmatory_seed_cohort\n"
            for seed in request.confirmatory_seeds
        )
        + "31,confirmatory_bootstrap,locked_analysis_seed\n"
        + "29,anchor_analysis,locked_analysis_seed\n"
        + "42,cluster_initialization,locked_cluster_random_state\n"
        + "NA,calibration_subsample_replicate,sha256-derived training_seed|population|client|replicate\n"
        + "NA,federated_client_round_stream,derive_worker_seed(training_seed;round;client;stream)\n"
        + "NA,fedavg_local_fine_tuning,derive_worker_seed(training_seed;dataset;population;client;purpose)\n",
        encoding="utf-8",
    )
    (request.root / "ENVIRONMENT" / "runtime.txt").write_text(
        "\n".join(
            (
                f"python={version.replace(chr(10), ' ')}",
                f"os={platform()}",
                f"cpu={processor() or 'NA'}",
                f"numpy={_installed_version('numpy')}",
                f"scipy={_installed_version('scipy')}",
                f"scikit-learn={_installed_version('scikit-learn')}",
                f"torch={_installed_version('torch')}",
                f"datasketches={_installed_version('datasketches')}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (request.root / "README_REPRODUCIBILITY.md").write_text(
        "# Reproducibility release\n\n"
        f"State: `{request.state.value}`. Validate this bundle with `datp-core validate-release <root>`.\n",
        encoding="utf-8",
    )


def _copy_release_artifact(root: Path, artifact: ReleaseArtifact) -> None:
    destination = root / artifact.relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(artifact.source, destination)


def _installed_version(distribution: str) -> str:
    try:
        return package_version(distribution)
    except PackageNotFoundError:
        return "NA"


def _write_manifest(root: Path, artifacts: tuple[ReleaseArtifact, ...]) -> None:
    entries = tuple(
        _entry_from_file(root, relative_path, artifact)
        for relative_path, artifact in _generated_release_artifacts(root, artifacts)
    )
    path = root / _MANIFEST_FILENAME
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_MANIFEST_COLUMNS)
        writer.writerows(
            (
                str(entry.relative_path),
                entry.digest,
                entry.byte_count,
                entry.artifact_type,
                entry.dataset_id,
                entry.population_id,
                entry.training_method,
                entry.training_seed,
                entry.threshold_policy,
                entry.experiment_id,
            )
            for entry in entries
        )
    (root / _SIDECAR_FILENAME).write_text(
        f"{_sha256_file(path)}  {_MANIFEST_FILENAME}\n",
        encoding="utf-8",
    )


def _generated_release_artifacts(
    root: Path,
    artifacts: tuple[ReleaseArtifact, ...],
) -> tuple[tuple[Path, ReleaseArtifact], ...]:
    generated = (
        ReleaseArtifact(root / _ROADMAP_LOCK_FILENAME, Path(_ROADMAP_LOCK_FILENAME), "roadmap_lock"),
        ReleaseArtifact(root / "SEEDS.csv", Path("SEEDS.csv"), "seed_registry"),
        ReleaseArtifact(root / "README_REPRODUCIBILITY.md", Path("README_REPRODUCIBILITY.md"), "readme"),
        ReleaseArtifact(root / "ENVIRONMENT" / "runtime.txt", Path("ENVIRONMENT/runtime.txt"), "environment"),
    )
    return tuple((item.relative_path, item) for item in (*generated, *artifacts))


def _entry_from_file(root: Path, relative_path: Path, artifact: ReleaseArtifact) -> ReleaseManifestEntry:
    path = root / relative_path
    return ReleaseManifestEntry(
        relative_path=relative_path,
        digest=_sha256_file(path),
        byte_count=path.stat().st_size,
        artifact_type=artifact.artifact_type,
        dataset_id=artifact.dataset_id,
        population_id=artifact.population_id,
        training_method=artifact.training_method,
        training_seed=artifact.training_seed,
        threshold_policy=artifact.threshold_policy,
        experiment_id=artifact.experiment_id,
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
    _require_relative_artifact_path(relative_path)
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


def _require_relative_artifact_path(relative_path: Path) -> None:
    if relative_path.is_absolute() or ".." in relative_path.parts or relative_path.name in {
        _MANIFEST_FILENAME,
        _SIDECAR_FILENAME,
    }:
        raise ArtifactIntegrityError(ErrorMessage("release manifest contains an invalid artifact path"))


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
