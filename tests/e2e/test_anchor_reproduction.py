from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.protocols.experiments import EXPERIMENTS


def test_anchor_reproduction_resolves_to_the_locked_federated_reference() -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.HISTORICAL_DATP_REPRODUCTION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="anchor fixture is available",
            ),
        ),
    )

    assert declaration.role is EvidenceRole.ANCHOR_REPRODUCTION
    assert declaration.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert declaration.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert frozenset(declaration.federated_thresholds) == frozenset(
        {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }
    )
    assert plan.executable == plan.entries
    assert all(entry.coordinate.population is declaration.population for entry in plan.entries)
    assert all(entry.coordinate.training_model is declaration.training_model for entry in plan.entries)
