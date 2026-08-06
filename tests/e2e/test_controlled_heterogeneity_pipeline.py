from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values.counts import Seed
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.seeds import SeedCohort


def test_controlled_heterogeneity_is_mechanism_evidence_not_a_second_confirmation() -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="controlled condition is resolved",
            ),
        ),
    )

    assert declaration.role is EvidenceRole.MECHANISM
    assert declaration.population is PopulationId.NBAIOT_DIRICHLET_CLIENTS
    assert declaration.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert frozenset(declaration.federated_thresholds) == frozenset(
        {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }
    )
    assert all(entry.coordinate.population is PopulationId.NBAIOT_DIRICHLET_CLIENTS for entry in plan.entries)
