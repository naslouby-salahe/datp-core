"""Centralized ``ExperimentPaths`` — the sole path authority for all DATP output.

All semantic output, shared-stage, training, checkpoint, score, calibration,
threshold, evaluation, analysis, freeze, report, diagnostic, and lifecycle paths
must be built through this authority. No other package may construct semantic
output paths independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.core.identifiers import ExperimentId


@dataclass(frozen=True, slots=True)
class ExperimentPaths:
    """Sole authority for all DATP semantic output paths.

    All methods are deterministic pure functions of their inputs. No method
    accesses the filesystem. Paths are relative to ``outputs_root`` unless
    explicitly scoped to ``repository_root``.
    """

    outputs_root: Path
    repository_root: Path

    # -- Experiment lifecycle -------------------------------------------------

    def experiment_root(self, experiment_id: ExperimentId) -> Path:
        return self.outputs_root / "experiments" / experiment_id.value

    def completion_marker(self, experiment_id: ExperimentId) -> Path:
        return self.experiment_root(experiment_id) / "COMPLETED"

    def manifest(self, experiment_id: ExperimentId) -> Path:
        return self.experiment_root(experiment_id) / "manifest.json"

    def status(self, experiment_id: ExperimentId) -> Path:
        return self.experiment_root(experiment_id) / "status.json"

    def failure(self, experiment_id: ExperimentId) -> Path:
        return self.experiment_root(experiment_id) / "failure.json"

    # -- Shared-stage paths ---------------------------------------------------

    def shared_materialization(self, ordinal: int, output_name: str) -> Path:
        return self.outputs_root / "shared" / "materializations" / f"{ordinal:04d}" / output_name

    def shared_training(self, ordinal: int, output_name: str) -> Path:
        return self.outputs_root / "shared" / "training" / f"{ordinal:04d}" / output_name

    def shared_checkpoint_selection(self, ordinal: int, output_name: str) -> Path:
        return self.outputs_root / "shared" / "checkpoint-selection" / f"{ordinal:04d}" / output_name

    def shared_scores(self, ordinal: int, output_name: str) -> Path:
        return self.outputs_root / "shared" / "scores" / f"{ordinal:04d}" / output_name

    def shared_root(self) -> Path:
        return self.outputs_root / "shared"

    # -- Diagnostics ----------------------------------------------------------

    def diagnostic_root(self) -> Path:
        return self.repository_root / ".tmp" / "diagnostics"
