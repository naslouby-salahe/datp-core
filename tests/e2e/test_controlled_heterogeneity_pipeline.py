from datp_core.app.planning import PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.core.identifiers import (
    CalibrationSupportLevel,
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


def test_controlled_heterogeneity_is_supportive_evidence_not_a_second_confirmation() -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("controlled condition is resolved"),
            ),
        ),
    )

    assert declaration.role is EvidenceRole.SUPPORTIVE
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


def test_heterogeneity_support_interaction_enumerates_every_locked_cell() -> None:
    declaration = next(
        item for item in EXPERIMENTS if item.id is ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION
    )
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("interaction conditions are resolved"),
            ),
        ),
    )

    support_cells = frozenset(
        (entry.coordinate.calibration_support, entry.coordinate.calibration_replicate) for entry in plan.entries
    )
    assert (CalibrationSupportLevel.FULL, None) in support_cells
    for support in (CalibrationSupportLevel.M50, CalibrationSupportLevel.M100, CalibrationSupportLevel.M500):
        assert sum(1 for level, _ in support_cells if level is support) == 10
    assert frozenset(entry.coordinate.threshold_method for entry in plan.entries) == frozenset(
        {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
            FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
            FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        }
    )
