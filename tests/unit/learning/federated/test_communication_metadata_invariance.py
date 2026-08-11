from tests.unit.learning.federated.helpers import AUTOENCODER

from datp_core.core.numeric import Seed
from datp_core.detector.autoencoder import AutoencoderModelState, build_reconstruction_autoencoder
from datp_core.detector.training.engine import serialize_model_state


def test_serialized_state_evidence_is_invariant_across_different_parameter_values() -> None:
    initial_model = build_reconstruction_autoencoder(AUTOENCODER, initialization_seed=Seed(0))
    initial_state = AutoencoderModelState.from_model(initial_model)

    retrained_model = build_reconstruction_autoencoder(AUTOENCODER, initialization_seed=Seed(1))
    retrained_state = AutoencoderModelState.from_model(retrained_model)

    assert not initial_state.is_equivalent_to(retrained_state)

    initial_evidence = serialize_model_state(initial_state)
    retrained_evidence = serialize_model_state(retrained_state)

    assert initial_evidence.byte_count == retrained_evidence.byte_count
    assert initial_evidence.logical_element_count == retrained_evidence.logical_element_count
