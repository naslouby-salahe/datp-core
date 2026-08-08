from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution.engine import build_campaign
from datp_core.experiments.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.protocols.experiments import EXPERIMENTS


def test_confirmatory_campaign_changes_threshold_scope_only() -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    evidence = PlanningEvidence(
        experiment=declaration.id,
        disposition=PlanDisposition.EXECUTABLE,
        reason="confirmatory fixture is complete",
    )
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0), Seed(1))),
        evidence=(evidence,),
    )
    campaign = build_campaign(plan)

    assert campaign == build_campaign(plan)
    assert declaration.role is EvidenceRole.CONFIRMATORY
    assert declaration.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert declaration.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert MetricId.FPR_COEFFICIENT_OF_VARIATION in declaration.metrics
    assert frozenset(entry.coordinate.threshold_method for entry in campaign.entries) == frozenset(
        {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }
    )
    assert len(frozenset(entry.coordinate.population for entry in campaign.entries)) == 1
    assert len(frozenset(entry.coordinate.training_model for entry in campaign.entries)) == 1
