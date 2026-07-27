"""Dagster orchestration — canonical execution authority for DATP-Core.

Every CLI command, single-experiment execution, campaign, diagnostic, and
resumption path delegates to this package. Domain logic lives in the existing
packages (pipeline/, experiments/, learning/, etc.) and Dagster wraps them.
"""

from datp_core.orchestration.dagster_defs import build_dagster_definitions
from datp_core.orchestration.diagnostics import (
    CampaignDiagnosticResult,
    DiagnosticOutputRoot,
    ExperimentDiagnosticResult,
    ExperimentDiagnosticStatus,
    run_campaign_diagnostic,
    run_experiment_diagnostic,
)

__all__ = [
    "CampaignDiagnosticResult",
    "DiagnosticOutputRoot",
    "ExperimentDiagnosticResult",
    "ExperimentDiagnosticStatus",
    "build_dagster_definitions",
    "run_campaign_diagnostic",
    "run_experiment_diagnostic",
]
