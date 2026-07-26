"""Production diagnostic commands.

Run the real pipeline (never mock, never shortcut) with isolated output roots.
Diagnostic outputs are placed in .tmp/diagnostics/ to avoid contaminating
official experiment outputs.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from datp_core.core.identifiers import ExperimentId


class DiagnosticOutputRoot:
    """Isolated root for diagnostic output — never mixes with official outputs."""

    def __init__(self, base: Path) -> None:
        self._base = base
        self._base.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._base

    def cleanup(self) -> None:
        if self._base.exists():
            shutil.rmtree(self._base, ignore_errors=True)


def _resolve_bootstrap_env(profile: str = "smoke") -> None:
    """Set bootstrap environment variables if not already set."""
    os.environ.setdefault(
        "DATP_REPOSITORY_ROOT",
        str(Path(__file__).resolve().parent.parent.parent.parent),
    )
    os.environ.setdefault("DATP_EXECUTION_PROFILE", profile)


def run_experiment_diagnostic(
    experiment_id: str,
    *,
    seed_index: int = 0,
    profile: str = "smoke",
) -> dict:
    """Run one experiment through the real production pipeline with one seed.

    Output is isolated under .tmp/diagnostics/ — never touches official outputs.
    """
    _resolve_bootstrap_env(profile)

    from datp_core.app import build_application
    from datp_core.config.project import resolve_project_configuration

    base = Path(".tmp/diagnostics")
    DiagnosticOutputRoot(base)

    base.mkdir(parents=True, exist_ok=True)
    env_override = {
        "DATP_OUTPUTS_ROOT": str(base.resolve()),
    }
    for k, v in env_override.items():
        os.environ[k] = v

    config = resolve_project_configuration()
    exp_id = ExperimentId(experiment_id)

    experiment = config.experiments.get(exp_id)
    cohort = config.seed_cohorts[experiment.seed_cohort_id]
    seeds = cohort.training_seeds
    if seed_index >= len(seeds):
        seed_index = 0
    seed = seeds[seed_index]

    app = build_application()

    try:
        result = app.run_experiment.run(exp_id, override=True)
    except Exception as exc:
        return {
            "experiment_id": experiment_id,
            "seed": str(seed.value),
            "status": "diagnostic_failed",
            "error": str(exc),
        }

    return {
        "experiment_id": experiment_id,
        "seed": str(seed.value),
        "status": "completed" if result.success else "failed",
        "status_detail": result.status.value,
        "scientific_fingerprint": (result.manifest.scientific_fingerprint if result.manifest else None),
    }


def run_campaign_diagnostic(*, profile: str = "smoke") -> dict:
    """Run the complete campaign through the real pipeline, one seed per experiment.

    Output is isolated under .tmp/diagnostics/ — never touches official outputs.
    """
    _resolve_bootstrap_env(profile)

    base = Path(".tmp/diagnostics")
    DiagnosticOutputRoot(base)

    os.environ["DATP_OUTPUTS_ROOT"] = str(base.resolve())

    from datp_core.app import build_application

    app = build_application()
    report = app.run_campaign.run(override_all=True)

    return {
        "total": report.total_experiments,
        "completed_or_skipped": report.completed_or_skipped,
        "executed": report.executed,
        "blocked": report.blocked,
        "failed": report.failed,
        "success": report.success,
    }
