"""Experiment output management: folder lifecycle, status, manifest, and completion markers.

Owns the contract for what a valid experiment output looks like on disk.
"""

from __future__ import annotations

import json
import shutil
from enum import Enum
from pathlib import Path
from time import time

from attrs import define, field

from datp_core.core.identifiers import ExperimentId


class ExperimentStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED_EXISTING = "skipped_existing"


@define(frozen=True, slots=True, kw_only=True)
class ExperimentManifest:
    schema_version: int = 2
    experiment_name: str = field()
    evidence_role: str = field()
    final_status: str = field()
    configuration_fingerprint: str = field()
    scientific_fingerprint: str = field()
    source_data_fingerprint: str = field()
    code_revision: str = field()
    seed_cohort: str = field()
    populations: tuple[str, ...] = field()
    training_profile: str = field()
    checkpoint_profile: str = field()
    prerequisite_result_fingerprints: tuple[str, ...] = field(factory=tuple)
    start_timestamp: float = field(factory=time)
    completion_timestamp: float | None = None
    frozen_result_path: str | None = None
    report_paths: tuple[str, ...] = field(factory=tuple)
    checksum_summary: str | None = None


class ExperimentOutputManager:
    """Manages the lifecycle of one experiment's output folder."""

    def __init__(self, outputs_root: Path) -> None:
        self._root = Path(outputs_root)

    def experiment_dir(self, experiment_id: ExperimentId) -> Path:
        return self._root / "experiments" / experiment_id.value

    def exists(self, experiment_id: ExperimentId) -> bool:
        return self.experiment_dir(experiment_id).exists()

    def status(self, experiment_id: ExperimentId) -> ExperimentStatus | None:
        status_path = self.experiment_dir(experiment_id) / "status.json"
        if not status_path.exists():
            return None
        try:
            data = json.loads(status_path.read_text())
            return ExperimentStatus(data["status"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def is_completed(self, experiment_id: ExperimentId) -> bool:
        exp_dir = self.experiment_dir(experiment_id)
        if not exp_dir.exists():
            return False
        completed_marker = exp_dir / "COMPLETED"
        if not completed_marker.exists():
            return False
        status = self.status(experiment_id)
        return status is ExperimentStatus.COMPLETED

    def is_incomplete(self, experiment_id: ExperimentId) -> bool:
        """Returns True if output exists but is not a valid completed experiment."""
        exp_dir = self.experiment_dir(experiment_id)
        if not exp_dir.exists():
            return False
        return not self.is_completed(experiment_id)

    def validate_completed(self, experiment_id: ExperimentId) -> str | None:
        """Validate a completed experiment output. Returns None if valid, or an error message."""
        exp_dir = self.experiment_dir(experiment_id)
        if not exp_dir.exists():
            return f"Experiment '{experiment_id.value}' output folder does not exist"
        completed_marker = exp_dir / "COMPLETED"
        if not completed_marker.exists():
            return f"Experiment '{experiment_id.value}' is missing the COMPLETED marker"
        status = self.status(experiment_id)
        if status is None:
            return f"Experiment '{experiment_id.value}' is missing status.json"
        if status is not ExperimentStatus.COMPLETED:
            return f"Experiment '{experiment_id.value}' status is '{status.value}', not 'completed'"
        manifest_path = exp_dir / "manifest.json"
        if not manifest_path.exists():
            return f"Experiment '{experiment_id.value}' is missing manifest.json"
        try:
            data = json.loads(manifest_path.read_text())
            if data.get("final_status") != "completed":
                return f"Experiment '{experiment_id.value}' manifest final_status is not 'completed'"
        except json.JSONDecodeError:
            return f"Experiment '{experiment_id.value}' manifest.json is corrupt"
        return None

    def create(self, experiment_id: ExperimentId) -> Path:
        exp_dir = self.experiment_dir(experiment_id)
        exp_dir.mkdir(parents=True, exist_ok=True)
        self._write_status(experiment_id, ExperimentStatus.RUNNING)
        return exp_dir

    def mark_completed(self, experiment_id: ExperimentId) -> None:
        exp_dir = self.experiment_dir(experiment_id)
        self._write_status(experiment_id, ExperimentStatus.COMPLETED)
        (exp_dir / "COMPLETED").touch()

    def mark_failed(self, experiment_id: ExperimentId, error: str) -> None:
        exp_dir = self.experiment_dir(experiment_id)
        self._write_status(experiment_id, ExperimentStatus.FAILED)
        failure = {"error": error, "timestamp": time()}
        (exp_dir / "failure.json").write_text(json.dumps(failure, indent=2))

    def mark_blocked(self, experiment_id: ExperimentId, reason: str) -> None:
        exp_dir = self.experiment_dir(experiment_id)
        if not exp_dir.exists():
            exp_dir.mkdir(parents=True, exist_ok=True)
        self._write_status(experiment_id, ExperimentStatus.BLOCKED)
        failure = {"reason": reason, "timestamp": time()}
        (exp_dir / "failure.json").write_text(json.dumps(failure, indent=2))

    def delete(self, experiment_id: ExperimentId) -> None:
        exp_dir = self.experiment_dir(experiment_id)
        if exp_dir.exists():
            # Safety: resolve symlinks to ensure we don't follow them out of the output root
            resolved = exp_dir.resolve()
            root_resolved = self._root.resolve()
            if not str(resolved).startswith(str(root_resolved)):
                raise ValueError(
                    f"Refusing to delete '{resolved}' — resolved path is outside output root '{root_resolved}'"
                )
            shutil.rmtree(exp_dir)

    def _write_status(self, experiment_id: ExperimentId, status: ExperimentStatus) -> None:
        exp_dir = self.experiment_dir(experiment_id)
        status_path = exp_dir / "status.json"
        status_path.write_text(json.dumps({"status": status.value, "updated_at": time()}, indent=2))

    def list_experiment_dirs(self) -> tuple[Path, ...]:
        experiments_root = self._root / "experiments"
        if not experiments_root.exists():
            return ()
        return tuple(sorted(experiments_root.iterdir()))
