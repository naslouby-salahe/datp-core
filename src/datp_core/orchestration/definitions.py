"""Dagster definitions composed only from pipeline-backed adapters."""

from dagster import Definitions

from datp_core.orchestration.assets.data import deterministic_plan
from datp_core.orchestration.assets.detectors import confirmatory_campaign
from datp_core.orchestration.assets.evidence import confirmatory_evidence
from datp_core.orchestration.assets.thresholds import completed_thresholds
from datp_core.orchestration.jobs import CONFIRMATORY_JOB, PLAN_JOB
from datp_core.orchestration.resources import PIPELINE_PATHS

DEFINITIONS = Definitions(
    assets=(
        deterministic_plan,
        confirmatory_campaign,
        completed_thresholds,
        confirmatory_evidence,
    ),
    jobs=(PLAN_JOB, CONFIRMATORY_JOB),
    resources={"paths": PIPELINE_PATHS},
)
