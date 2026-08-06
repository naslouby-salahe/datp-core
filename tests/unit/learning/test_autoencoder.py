import pytest
import torch

from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import Seed
from datp_core.learning.autoencoder import (
    ReconstructionAutoencoder,
    build_reconstruction_autoencoder,
    clone_autoencoder_state,
    load_autoencoder_state,
)
from datp_core.protocols.training import AutoencoderProtocol


def test_forward_output_shape_equals_input_shape() -> None:
    model = ReconstructionAutoencoder((4, 3, 2, 3, 4))
    features = torch.randn(5, 4)
    output = model(features)
    assert output.shape == features.shape


def test_rejects_mismatched_input_and_output_widths() -> None:
    with pytest.raises(ScientificContractError, match="input and output widths"):
        ReconstructionAutoencoder((4, 3, 2))


def test_rejects_widths_shorter_than_two_layers() -> None:
    with pytest.raises(ScientificContractError, match="at least input and output"):
        ReconstructionAutoencoder((4,))


def test_no_batchnorm_or_dropout_layers_are_introduced() -> None:
    model = ReconstructionAutoencoder((4, 3, 2, 3, 4))
    for module in model.modules():
        assert not isinstance(module, torch.nn.BatchNorm1d)
        assert not isinstance(module, torch.nn.Dropout)


def test_initialization_is_deterministic_from_the_seed() -> None:
    protocol = AutoencoderProtocol(widths=(4, 3, 2, 3, 4))
    first = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(7))
    second = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(7))
    for left, right in zip(first.state_dict().values(), second.state_dict().values(), strict=True):
        assert torch.equal(left, right)


def test_different_seeds_produce_different_initializations() -> None:
    protocol = AutoencoderProtocol(widths=(4, 3, 2, 3, 4))
    first = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(1))
    second = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(2))
    mismatched = any(
        not torch.equal(left, right)
        for left, right in zip(first.state_dict().values(), second.state_dict().values(), strict=True)
    )
    assert mismatched


def test_clone_and_load_state_round_trips_exactly() -> None:
    protocol = AutoencoderProtocol(widths=(4, 3, 2, 3, 4))
    model = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(3))
    cloned = clone_autoencoder_state(model)
    other = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(4))
    load_autoencoder_state(other, cloned)
    for left, right in zip(model.state_dict().values(), other.state_dict().values(), strict=True):
        assert torch.equal(left, right)


def test_model_has_no_threshold_or_metric_attributes() -> None:
    model = ReconstructionAutoencoder((4, 3, 2, 3, 4))
    forbidden = {"threshold", "quantile", "auroc", "fpr"}
    attribute_names = {name for name, _ in model.named_parameters()} | set(dir(model))
    assert not any(term in name.lower() for name in attribute_names for term in forbidden)
