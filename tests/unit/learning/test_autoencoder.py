import pytest
import torch

from datp_core.core.errors import ScientificContractError
from datp_core.core.numeric import FeatureCount, Seed
from datp_core.detector.autoencoder import (
    AutoencoderModelState,
    ReconstructionAutoencoder,
    build_reconstruction_autoencoder,
)
from datp_core.detector.training.contracts import AutoencoderArchitecture, AutoencoderProtocol

_ARCHITECTURE = AutoencoderArchitecture(
    (FeatureCount(4), FeatureCount(3), FeatureCount(2), FeatureCount(3), FeatureCount(4))
)


def test_forward_output_shape_equals_input_shape() -> None:
    model = ReconstructionAutoencoder(_ARCHITECTURE)
    features = torch.randn(5, 4)
    output = model(features)
    assert output.shape == features.shape


def test_rejects_mismatched_input_and_output_widths() -> None:
    widths = (FeatureCount(4), FeatureCount(3), FeatureCount(2))
    with pytest.raises(ScientificContractError, match="input and output widths"):
        AutoencoderArchitecture(widths)


def test_rejects_widths_shorter_than_two_layers() -> None:
    widths = (FeatureCount(4),)
    with pytest.raises(ScientificContractError, match="at least input and output"):
        AutoencoderArchitecture(widths)


def test_no_batchnorm_or_dropout_layers_are_introduced() -> None:
    model = ReconstructionAutoencoder(_ARCHITECTURE)
    for module in model.modules():
        assert not isinstance(module, torch.nn.BatchNorm1d)
        assert not isinstance(module, torch.nn.Dropout)


def test_initialization_is_deterministic_from_the_seed() -> None:
    protocol = AutoencoderProtocol(widths=_ARCHITECTURE)
    first = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(7))
    second = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(7))
    for left, right in zip(first.state_dict().values(), second.state_dict().values(), strict=True):
        assert torch.equal(left, right)


def test_different_seeds_produce_different_initializations() -> None:
    protocol = AutoencoderProtocol(widths=_ARCHITECTURE)
    first = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(1))
    second = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(2))
    mismatched = any(
        not torch.equal(left, right)
        for left, right in zip(first.state_dict().values(), second.state_dict().values(), strict=True)
    )
    assert mismatched


def test_clone_and_load_state_round_trips_exactly() -> None:
    protocol = AutoencoderProtocol(widths=_ARCHITECTURE)
    model = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(3))
    cloned = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
    other = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(4))
    other.load_state_dict(cloned, strict=True)
    for left, right in zip(model.state_dict().values(), other.state_dict().values(), strict=True):
        assert torch.equal(left, right)


def test_model_state_owns_captured_and_exported_tensors() -> None:
    protocol = AutoencoderProtocol(widths=_ARCHITECTURE)
    model = build_reconstruction_autoencoder(protocol, initialization_seed=Seed(3))
    model_state = AutoencoderModelState.from_model(model)
    expected = model_state.to_torch_state_dict()

    with torch.no_grad():
        next(model.parameters()).zero_()
    exported = model_state.to_torch_state_dict()
    next(iter(exported.values())).zero_()

    assert model_state.is_equivalent_to(AutoencoderModelState.from_torch_state_dict(expected))


def test_model_has_no_threshold_or_metric_attributes() -> None:
    model = ReconstructionAutoencoder(_ARCHITECTURE)
    forbidden = {"threshold", "quantile", "auroc", "fpr"}
    attribute_names = {name for name, _ in model.named_parameters()} | set(dir(model))
    assert not any(term in name.lower() for name in attribute_names for term in forbidden)
