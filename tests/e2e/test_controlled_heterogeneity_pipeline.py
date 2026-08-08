from datp_core.app.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import Seed
from datp_core.data.populations.contracts import ControlledPartitionKind
from datp_core.data.populations.declarations import DIRICHLET_CONCENTRATIONS
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.registry import EXPERIMENTS


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
    partition_kinds = frozenset(entry.coordinate.controlled_partition_kind for entry in plan.entries)
    assert ControlledPartitionKind.DIRICHLET in partition_kinds
    assert ControlledPartitionKind.IID in partition_kinds
    concentrations = frozenset(
        entry.coordinate.dirichlet_concentration.value
        for entry in plan.entries
        if entry.coordinate.dirichlet_concentration is not None
    )
    assert concentrations == frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
    assert all(entry.coordinate.controlled_partition_kind is not None for entry in plan.entries)
