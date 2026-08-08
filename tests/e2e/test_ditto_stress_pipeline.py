from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.experiments.registry import EXPERIMENTS


def test_ditto_personalization_cannot_replace_the_confirmatory_detector() -> None:
    confirmatory = next(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    ditto = next(item for item in EXPERIMENTS if item.id is ExperimentId.DITTO_ABSORPTION_STRESS_TEST)

    assert ditto.role is EvidenceRole.TRAINING_STRESS_TEST
    assert ditto.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert ditto.training_model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER
    assert ditto.training_model is not confirmatory.training_model
    assert ditto.federated_thresholds == (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    )
