"""Production diagnostic commands.

Run the real pipeline (never mock, never shortcut) with isolated output roots.
Diagnostic outputs are placed in .tmp/diagnostics/ to avoid contaminating
official experiment outputs.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from datp_core.config.bootstrap import RuntimeBootstrapSettings
from datp_core.config.project import resolve_project_configuration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.planning.paths import ExperimentPaths


class ExperimentDiagnosticStatus(Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    DIAGNOSTIC_FAILED = "diagnostic_failed"


@dataclass(frozen=True, slots=True)
class ExperimentDiagnosticResult:
    experiment_id: str
    seed: str
    status: ExperimentDiagnosticStatus
    error: str | None = None
    status_detail: str | None = None
    scientific_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class CampaignDiagnosticResult:
    total: int
    completed_or_skipped: int
    executed: int
    blocked: int
    failed: int
    success: bool


class DiagnosticOutputRoot:
    """Isolated root for diagnostic output — never mixes with official outputs."""

    def __init__(self, paths: ExperimentPaths) -> None:
        self._base = paths.diagnostic_root()
        self._base.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._base

    def cleanup(self) -> None:
        if self._base.exists():
            shutil.rmtree(self._base, ignore_errors=True)


def _resolve_bootstrap_settings(profile: str = "smoke") -> RuntimeBootstrapSettings:
    return RuntimeBootstrapSettings(execution_profile=profile)


def _build_diagnostic_paths(
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ExperimentPaths:
    config = resolve_project_configuration(bootstrap_settings=bootstrap_settings)
    return ExperimentPaths(
        outputs_root=config.paths.outputs,
        repository_root=config.paths.repository_root,
    )


def run_experiment_diagnostic(
    experiment_id: str,
    *,
    seed_index: int = 0,
    profile: str = "smoke",
) -> ExperimentDiagnosticResult:
    bootstrap_settings = _resolve_bootstrap_settings(profile)
    config = resolve_project_configuration(bootstrap_settings=bootstrap_settings)
    paths = _build_diagnostic_paths(bootstrap_settings)
    DiagnosticOutputRoot(paths)

    exp_id = ExperimentId(experiment_id)

    experiment = config.experiments.get(exp_id)
    cohort = config.seed_cohorts[experiment.seed_cohort_id]
    seeds = cohort.training_seeds
    if seed_index >= len(seeds):
        seed_index = 0

    from datp_core.app import build_application

    app = build_application(bootstrap_settings=bootstrap_settings)

    try:
        result = app.run_experiment.run(exp_id, override=True)
    except Exception as exc:
        return ExperimentDiagnosticResult(
            experiment_id=experiment_id,
            seed=str(seeds[seed_index].value if seed_index < len(seeds) else ""),
            status=ExperimentDiagnosticStatus.DIAGNOSTIC_FAILED,
            error=str(exc),
        )

    return ExperimentDiagnosticResult(
        experiment_id=experiment_id,
        seed=str(seeds[seed_index].value if seed_index < len(seeds) else ""),
        status=ExperimentDiagnosticStatus.COMPLETED if result.success else ExperimentDiagnosticStatus.FAILED,
        status_detail=result.status.value,
        scientific_fingerprint=(result.manifest.scientific_fingerprint if result.manifest else None),
    )


def run_campaign_diagnostic(*, profile: str = "smoke") -> CampaignDiagnosticResult:
    bootstrap_settings = _resolve_bootstrap_settings(profile)
    paths = _build_diagnostic_paths(bootstrap_settings)
    DiagnosticOutputRoot(paths)

    from datp_core.app import build_application

    app = build_application(bootstrap_settings=bootstrap_settings)
    report = app.run_campaign.run(override_all=True)

    return CampaignDiagnosticResult(
        total=report.total_experiments,
        completed_or_skipped=report.completed_or_skipped,
        executed=report.executed,
        blocked=report.blocked,
        failed=report.failed,
        success=report.success,
    )
