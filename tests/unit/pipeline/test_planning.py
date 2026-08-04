from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values import Seed
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort


def test_plan_expansion_is_deterministic_and_records_blockers() -> None:
    declaration = ExperimentDeclaration(
        id=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        role=EvidenceRole.CONFIRMATORY,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        metrics=(MetricId.FPR_COEFFICIENT_OF_VARIATION,),
        readiness=ExperimentReadiness.DECLARED,
    )
    evidence = (
        PlanningEvidence(
            experiment=declaration.id,
            disposition=PlanDisposition.EXECUTABLE,
            reason="all prerequisites validated",
        ),
    )
    first = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0), Seed(1))),
        evidence=evidence,
    )
    second = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0), Seed(1))),
        evidence=evidence,
    )
    assert first == second
    assert len(first.entries) == 4
    assert all(entry.disposition is PlanDisposition.EXECUTABLE for entry in first.entries)
