"""Lifecycle and integrity checks for one experiment's direct output directory."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from time import time

from datp_core.artifacts.atomic import atomic_write_bytes
from datp_core.artifacts.provenance import git_revision
from datp_core.core.identifiers import ExperimentId


class ExperimentStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OutputState(Enum):
    ABSENT = "absent"
    VALID_COMPLETED = "valid_completed"
    INCOMPLETE = "incomplete"
    CORRUPT = "corrupt"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """The sole persisted provenance record for a completed experiment."""

    schema_version: int
    experiment_name: str
    final_status: str
    scientific_fingerprint: str
    execution_fingerprint: str
    code_revision: str
    source_data_fingerprint: str
    prerequisite_result_fingerprints: dict[str, str] = field(default_factory=dict)
    frozen_result_path: str = ""
    frozen_result_fingerprint: str = ""
    report_paths: tuple[str, ...] = ()
    checksums: dict[str, str] = field(default_factory=dict)
    start_timestamp: float = 0.0
    completion_timestamp: float = 0.0

    @classmethod
    def from_dict(cls, raw: object) -> ExperimentManifest:
        if not isinstance(raw, dict):
            raise ValueError("manifest root must be an object")
        required = {
            "schema_version",
            "experiment_name",
            "final_status",
            "scientific_fingerprint",
            "execution_fingerprint",
            "code_revision",
            "source_data_fingerprint",
            "prerequisite_result_fingerprints",
            "frozen_result_path",
            "frozen_result_fingerprint",
            "report_paths",
            "checksums",
            "start_timestamp",
            "completion_timestamp",
        }
        if set(raw) != required:
            raise ValueError(f"manifest fields differ from the completion contract: {sorted(set(raw) ^ required)}")
        prerequisites = raw["prerequisite_result_fingerprints"]
        checksums = raw["checksums"]
        reports = raw["report_paths"]
        if (
            not isinstance(prerequisites, dict)
            or not all(isinstance(key, str) and isinstance(value, str) for key, value in prerequisites.items())
            or not isinstance(checksums, dict)
            or not all(isinstance(key, str) and isinstance(value, str) for key, value in checksums.items())
            or not isinstance(reports, list)
            or not all(isinstance(value, str) for value in reports)
        ):
            raise ValueError("manifest paths, checksums, and prerequisite fingerprints must be string collections")
        scalar_names = (
            "experiment_name",
            "final_status",
            "scientific_fingerprint",
            "execution_fingerprint",
            "code_revision",
            "source_data_fingerprint",
            "frozen_result_path",
            "frozen_result_fingerprint",
        )
        if any(not isinstance(raw[name], str) for name in scalar_names):
            raise ValueError("manifest fingerprint and path fields must be strings")
        if not isinstance(raw["schema_version"], int) or any(
            not isinstance(raw[name], (int, float)) for name in ("start_timestamp", "completion_timestamp")
        ):
            raise ValueError("manifest schema/timestamp fields have invalid types")
        return cls(
            schema_version=raw["schema_version"],
            experiment_name=raw["experiment_name"],
            final_status=raw["final_status"],
            scientific_fingerprint=raw["scientific_fingerprint"],
            execution_fingerprint=raw["execution_fingerprint"],
            code_revision=raw["code_revision"],
            source_data_fingerprint=raw["source_data_fingerprint"],
            prerequisite_result_fingerprints=dict(prerequisites),
            frozen_result_path=raw["frozen_result_path"],
            frozen_result_fingerprint=raw["frozen_result_fingerprint"],
            report_paths=tuple(reports),
            checksums=dict(checksums),
            start_timestamp=float(raw["start_timestamp"]),
            completion_timestamp=float(raw["completion_timestamp"]),
        )


@dataclass(frozen=True, slots=True)
class OutputInspection:
    state: OutputState
    reason: str | None = None
    manifest: ExperimentManifest | None = None


class ExperimentOutputManager:
    """Owns only experiment-folder lifecycle, final inventory, and validation."""

    _MANIFEST = "manifest.json"
    _STATUS = "status.json"
    _COMPLETED = "COMPLETED"
    _FAILURE = "failure.json"
    _LIFECYCLE_FILES = frozenset({_MANIFEST, _STATUS, _COMPLETED, _FAILURE})

    def __init__(self, outputs_root: Path) -> None:
        self._root = Path(outputs_root)

    def experiment_dir(self, experiment_id: ExperimentId) -> Path:
        return self._root / "experiments" / experiment_id.value

    def exists(self, experiment_id: ExperimentId) -> bool:
        return self.experiment_dir(experiment_id).exists()

    def begin(self, experiment_id: ExperimentId) -> Path:
        directory = self.experiment_dir(experiment_id)
        if directory.exists():
            raise FileExistsError(f"Experiment output already exists: {directory}")
        directory.mkdir(parents=True)
        self._write_json(directory / self._STATUS, {"status": ExperimentStatus.RUNNING.value, "updated_at": time()})
        return directory

    def mark_failed(self, experiment_id: ExperimentId, error: str) -> None:
        directory = self._require_experiment_dir(experiment_id)
        self._write_json(directory / self._STATUS, {"status": ExperimentStatus.FAILED.value, "updated_at": time()})
        self._write_json(directory / self._FAILURE, {"error": error, "timestamp": time()})

    def inspect(
        self,
        experiment_id: ExperimentId,
        *,
        scientific_fingerprint: str | None = None,
        execution_fingerprint: str | None = None,
        source_data_fingerprint: str | None = None,
        prerequisite_result_fingerprints: dict[str, str] | None = None,
    ) -> OutputInspection:
        directory = self.experiment_dir(experiment_id)
        if not directory.exists():
            return OutputInspection(OutputState.ABSENT)
        if directory.is_symlink() or not directory.is_dir():
            return OutputInspection(OutputState.CORRUPT, "experiment output is not a regular directory")
        status = self._read_status(directory)
        if status is None:
            return OutputInspection(OutputState.CORRUPT, "status.json is missing or corrupt")
        marker = directory / self._COMPLETED
        if status is not ExperimentStatus.COMPLETED or not marker.is_file():
            return OutputInspection(
                OutputState.INCOMPLETE,
                f"experiment status is '{status.value}' or COMPLETED is absent",
            )
        manifest_path = directory / self._MANIFEST
        if not manifest_path.is_file():
            return OutputInspection(OutputState.INCOMPLETE, "completed output is missing manifest.json")
        if marker.stat().st_mtime_ns < manifest_path.stat().st_mtime_ns:
            return OutputInspection(OutputState.CORRUPT, "COMPLETED predates the final manifest")
        try:
            manifest = ExperimentManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return OutputInspection(OutputState.CORRUPT, f"manifest.json is corrupt: {exc}")
        if manifest.experiment_name != experiment_id.value or manifest.final_status != ExperimentStatus.COMPLETED.value:
            return OutputInspection(OutputState.CORRUPT, "manifest does not describe a completed selected experiment")
        if scientific_fingerprint is not None and manifest.scientific_fingerprint != scientific_fingerprint:
            return OutputInspection(
                OutputState.INCOMPATIBLE,
                "scientific_fingerprint differs from current configuration",
                manifest,
            )
        if execution_fingerprint is not None and manifest.execution_fingerprint != execution_fingerprint:
            return OutputInspection(
                OutputState.INCOMPATIBLE,
                "execution_fingerprint differs from current configuration",
                manifest,
            )
        if source_data_fingerprint is not None and manifest.source_data_fingerprint != source_data_fingerprint:
            return OutputInspection(
                OutputState.INCOMPATIBLE,
                "source_data_fingerprint differs from current configuration",
                manifest,
            )
        if (
            prerequisite_result_fingerprints is not None
            and manifest.prerequisite_result_fingerprints != prerequisite_result_fingerprints
        ):
            return OutputInspection(
                OutputState.INCOMPATIBLE,
                "prerequisite frozen-result fingerprints differ",
                manifest,
            )
        validation_error = self._validate_inventory(directory, manifest)
        if validation_error is not None:
            return OutputInspection(OutputState.CORRUPT, validation_error, manifest)
        return OutputInspection(OutputState.VALID_COMPLETED, manifest=manifest)

    def finalize_from_directory(
        self,
        experiment_id: ExperimentId,
        *,
        scientific_fingerprint: str,
        execution_fingerprint: str,
        source_data_fingerprint: str,
        prerequisite_result_fingerprints: dict[str, str],
        started_at: float,
    ) -> ExperimentManifest:
        """Record direct files produced by this fresh run, then write completion marker last."""
        directory = self._require_experiment_dir(experiment_id)
        if self._read_status(directory) is not ExperimentStatus.RUNNING:
            raise ValueError(f"Cannot finalize experiment '{experiment_id.value}' that is not RUNNING")
        frozen = self._discover_frozen_result(directory)
        reports = self._discover_reports(directory)
        checksums = self._checksum_inventory(directory)
        frozen_relative = frozen.relative_to(directory).as_posix()
        if frozen_relative not in checksums:
            raise ValueError("frozen result is missing from direct output inventory")
        manifest = ExperimentManifest(
            schema_version=1,
            experiment_name=experiment_id.value,
            final_status=ExperimentStatus.COMPLETED.value,
            scientific_fingerprint=scientific_fingerprint,
            execution_fingerprint=execution_fingerprint,
            code_revision=git_revision(),
            source_data_fingerprint=source_data_fingerprint,
            prerequisite_result_fingerprints=dict(sorted(prerequisite_result_fingerprints.items())),
            frozen_result_path=frozen_relative,
            frozen_result_fingerprint=checksums[frozen_relative],
            report_paths=tuple(path.relative_to(directory).as_posix() for path in reports),
            checksums=checksums,
            start_timestamp=started_at,
            completion_timestamp=time(),
        )
        self._write_json(directory / self._MANIFEST, asdict(manifest))
        self._write_json(directory / self._STATUS, {"status": ExperimentStatus.COMPLETED.value, "updated_at": time()})
        atomic_write_bytes(directory / self._COMPLETED, b"", prefix=".tmp_lifecycle_")
        return manifest

    def delete(self, experiment_id: ExperimentId) -> None:
        root = self._resolved_output_root()
        experiments_root = root / "experiments"
        if experiments_root.is_symlink():
            raise ValueError("Refusing to delete from a symlinked experiments output root")
        if experiments_root.exists() and not experiments_root.is_dir():
            raise ValueError("Experiment output root is not a directory")
        if ExperimentId(experiment_id.value) != experiment_id:
            raise ValueError(f"Invalid experiment identifier: {experiment_id!r}")
        directory = experiments_root / experiment_id.value
        if not directory.exists():
            return
        if (
            directory.parent != experiments_root
            or directory.is_symlink()
            or not directory.is_dir()
            or directory.resolve().parent != experiments_root.resolve()
        ):
            raise ValueError(f"Refusing to delete unsafe experiment output: {directory}")
        shutil.rmtree(directory)

    def delete_shared_outputs(self) -> None:
        """Delete only the campaign-managed shared directory after independently deleting experiments."""
        root = self._resolved_output_root()
        shared = root / "shared"
        if not shared.exists():
            return
        if shared.is_symlink() or not shared.is_dir() or shared.resolve().parent != root:
            raise ValueError(f"Refusing to delete unsafe shared output: {shared}")
        shutil.rmtree(shared)

    def is_completed(self, experiment_id: ExperimentId) -> bool:
        return self.inspect(experiment_id).state is OutputState.VALID_COMPLETED

    def is_incomplete(self, experiment_id: ExperimentId) -> bool:
        return self.inspect(experiment_id).state in {OutputState.INCOMPLETE, OutputState.CORRUPT}

    def load_frozen_result(
        self,
        experiment_id: ExperimentId,
        manifest: ExperimentManifest | None = None,
    ) -> dict[str, object]:
        """Load the completed experiment's one frozen JSON result without reconstructing stage paths."""
        resolved_manifest = manifest or self.inspect(experiment_id).manifest
        if resolved_manifest is None:
            raise ValueError(f"Experiment '{experiment_id.value}' has no validated final manifest")
        path = self._safe_relative(self.experiment_dir(experiment_id), resolved_manifest.frozen_result_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Frozen result for '{experiment_id.value}' is unreadable: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Frozen result for '{experiment_id.value}' must be a JSON object")
        return payload

    def _discover_frozen_result(self, directory: Path) -> Path:
        candidates = [
            directory / "frozen-result.json",
            directory / "frozen_result.json",
        ]
        candidates.extend(
            path for name in ("frozen_result", "frozen-result") for path in (directory / name).rglob("*.json")
        )
        regular_candidates = [path for path in candidates if path.is_file() and not path.is_symlink()]
        if len(regular_candidates) != 1:
            raise ValueError("Fresh experiment must contain exactly one frozen-result JSON file")
        return regular_candidates[0]

    def _discover_reports(self, directory: Path) -> tuple[Path, ...]:
        reports_root = directory / "reports"
        reports = tuple(
            sorted(
                (path for path in reports_root.rglob("*") if path.is_file() and not path.is_symlink()),
                key=str,
            )
        )
        if not reports:
            raise ValueError("Fresh experiment must contain at least one report under reports/")
        return reports

    def _checksum_inventory(self, directory: Path) -> dict[str, str]:
        inventory: dict[str, str] = {}
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Experiment output may not contain symlinks: {path}")
            if not path.is_file() or path.relative_to(directory).as_posix() in self._LIFECYCLE_FILES:
                continue
            relative = path.relative_to(directory).as_posix()
            inventory[relative] = self._checksum(path)
        return dict(sorted(inventory.items()))

    def _validate_inventory(self, directory: Path, manifest: ExperimentManifest) -> str | None:
        if not manifest.frozen_result_path or not manifest.frozen_result_fingerprint:
            return "manifest lacks frozen-result path or fingerprint"
        if not manifest.report_paths:
            return "manifest lacks required report paths"
        if manifest.frozen_result_path not in manifest.checksums:
            return "manifest inventory omits frozen result"
        if manifest.checksums[manifest.frozen_result_path] != manifest.frozen_result_fingerprint:
            return "manifest frozen-result checksum disagrees with inventory"
        if any(report not in manifest.checksums for report in manifest.report_paths):
            return "manifest inventory omits a required report"
        try:
            actual_inventory = self._checksum_inventory(directory)
        except ValueError as exc:
            return str(exc)
        if set(actual_inventory) != set(manifest.checksums):
            return "manifest inventory does not exactly match experiment output files"
        for relative, expected in manifest.checksums.items():
            try:
                path = self._safe_relative(directory, relative)
            except ValueError as exc:
                return str(exc)
            if not path.is_file() or path.is_symlink():
                return f"required output is missing: {relative}"
            if self._checksum(path) != expected:
                return f"checksum mismatch for output: {relative}"
        return None

    def _require_experiment_dir(self, experiment_id: ExperimentId) -> Path:
        directory = self.experiment_dir(experiment_id)
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f"Experiment output directory is missing or unsafe: {directory}")
        return directory

    def _resolved_output_root(self) -> Path:
        if self._root.is_symlink():
            raise ValueError("Refusing to delete through a symlinked output root")
        resolved = self._root.resolve()
        if resolved.is_symlink() or (resolved.exists() and not resolved.is_dir()):
            raise ValueError("Configured output root is unsafe")
        return resolved

    def _read_status(self, directory: Path) -> ExperimentStatus | None:
        try:
            raw = json.loads((directory / self._STATUS).read_text(encoding="utf-8"))
            return ExperimentStatus(raw["status"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.blake2b(digest_size=32)
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1_048_576), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _safe_relative(directory: Path, relative_path: str) -> Path:
        relative = Path(relative_path)
        if not relative_path or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"manifest contains unsafe output path: {relative_path!r}")
        path = directory
        for part in relative.parts:
            path /= part
            if path.is_symlink():
                raise ValueError(f"manifest output path traverses a symlink: {relative_path!r}")
        return path

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        atomic_write_bytes(
            path,
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"),
            prefix=".tmp_lifecycle_",
        )


__all__ = ["ExperimentManifest", "ExperimentOutputManager", "ExperimentStatus", "OutputInspection", "OutputState"]
