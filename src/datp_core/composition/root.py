"""DatpApplication composition root assembling application use cases."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.application.artifact_management import ArtifactManagementUseCase
from datp_core.application.configuration import (
    DescribeCatalogueUseCase,
    ExplainConfigurationDriftUseCase,
    ValidateConfigurationUseCase,
)
from datp_core.application.dataset_audit import AuditDatasetUseCase
from datp_core.application.experiment_execution import ExecuteExperimentUseCase, ResumeExperimentUseCase
from datp_core.application.experiment_planning import PlanExperimentUseCase
from datp_core.application.result_audit import AuditResultsUseCase, QueryResultsUseCase
from datp_core.application.statistical_analysis import StatisticalAnalysisUseCase
from datp_core.application.threshold_construction import ConstructThresholdsUseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class DatpApplication:
    """Composition root exposing explicit application use cases."""

    validate_configuration: ValidateConfigurationUseCase
    describe_catalogue: DescribeCatalogueUseCase
    explain_configuration_drift: ExplainConfigurationDriftUseCase
    audit_dataset: AuditDatasetUseCase
    plan_experiment: PlanExperimentUseCase
    execute_experiment: ExecuteExperimentUseCase
    resume_experiment: ResumeExperimentUseCase
    construct_thresholds: ConstructThresholdsUseCase
    statistical_analysis: StatisticalAnalysisUseCase
    artifact_management: ArtifactManagementUseCase
    audit_results: AuditResultsUseCase
    query_results: QueryResultsUseCase


def build_application() -> DatpApplication:
    return DatpApplication(
        validate_configuration=ValidateConfigurationUseCase(),
        describe_catalogue=DescribeCatalogueUseCase(),
        explain_configuration_drift=ExplainConfigurationDriftUseCase(),
        audit_dataset=AuditDatasetUseCase(),
        plan_experiment=PlanExperimentUseCase(),
        execute_experiment=ExecuteExperimentUseCase(),
        resume_experiment=ResumeExperimentUseCase(),
        construct_thresholds=ConstructThresholdsUseCase(),
        statistical_analysis=StatisticalAnalysisUseCase(),
        artifact_management=ArtifactManagementUseCase(),
        audit_results=AuditResultsUseCase(),
        query_results=QueryResultsUseCase(),
    )
