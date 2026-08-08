from datp_core.app.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.core.identifiers import EvidenceRole, ExperimentId, PopulationId, TrainingModelId
from datp_core.core.numeric import Seed
from datp_core.detector.training.protocols import FEDPROX_COEFFICIENTS
from datp_core.experiments.common.coordinates import ExecutionRoute, execution_route_for
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.registry import EXPERIMENTS
from datp_core.experiments.training_stress import run as personalization_workflow


def test_fedprox_is_a_separate_training_side_stress_pipeline() -> None:
    confirmatory = next(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    fedprox = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)

    assert fedprox.role is EvidenceRole.TRAINING_STRESS_TEST
    assert fedprox.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert fedprox.training_model is TrainingModelId.FEDPROX_AUTOENCODER
    assert fedprox.training_model is not confirmatory.training_model
    assert fedprox.id is not confirmatory.id


def test_fedprox_stress_entry_point_marks_experiment_executable_with_standard_route() -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="the FedProx stress-test entry point supplies the locked natural-device execution prerequisites",
            ),
        ),
    )
    executable = plan.executable
    assert executable
    assert all(entry.disposition is PlanDisposition.EXECUTABLE for entry in executable)
    assert all(execution_route_for(entry.coordinate) is ExecutionRoute.SINGLE_COORDINATE for entry in executable)
    coefficients = frozenset(
        entry.coordinate.model_coefficient.value
        for entry in executable
        if entry.coordinate.model_coefficient is not None
    )
    assert coefficients == frozenset(item.value for item in FEDPROX_COEFFICIENTS)
    assert hasattr(personalization_workflow, "run_fedprox_stress_test_seed")
    assert hasattr(personalization_workflow, "load_fedprox_cv_fpr_corners")
    assert hasattr(personalization_workflow, "build_fedprox_absorption_observation")
