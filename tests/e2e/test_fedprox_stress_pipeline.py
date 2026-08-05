from datp_core.domain.enums import EvidenceRole, ExperimentId, PopulationId, TrainingModelId
from datp_core.protocols.experiments import EXPERIMENTS


def test_fedprox_is_a_separate_training_side_stress_pipeline() -> None:
    confirmatory = next(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    fedprox = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)

    assert fedprox.role is EvidenceRole.TRAINING_STRESS_TEST
    assert fedprox.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert fedprox.training_model is TrainingModelId.FEDPROX_AUTOENCODER
    assert fedprox.training_model is not confirmatory.training_model
    assert fedprox.id is not confirmatory.id
