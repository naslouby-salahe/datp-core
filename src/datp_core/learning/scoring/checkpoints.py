"""Checkpoint model loading for reconstruction scoring.

Provides the sanctioned path for loading trained autoencoder models from persisted
checkpoint payloads, replacing direct ``safetensors.torch.load`` access with repository-backed
or bytes-based loading functions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from safetensors.torch import load as load_safetensors

from datp_core.learning.model.autoencoder import DynamicDenseAutoencoder


def build_model_from_state_dict(
    states: Mapping[str, object],
    prefix: str,
    input_dimension: int,
    hidden_dims: tuple[int, ...],
) -> DynamicDenseAutoencoder:
    """Construct and load a :class:`DynamicDenseAutoencoder` from a state-dict mapping.

    Parameters
    ----------
    states:
        Mapping of tensor names to tensors, typically decoded from a safetensors payload.
    prefix:
        Key prefix used to select the relevant round's state (e.g. ``"round_42."``).
    input_dimension:
        Number of input features for the autoencoder.
    hidden_dims:
        Hidden-layer dimensions used when constructing the autoencoder.
    """
    state = {name.removeprefix(prefix): tensor for name, tensor in states.items() if name.startswith(prefix)}
    if not state:
        raise ValueError("Selected checkpoint is absent from the persisted checkpoint grid")
    model = DynamicDenseAutoencoder(input_dimension, hidden_dims)
    model.load_state_dict(state)
    model.eval()
    return model


def build_model_from_checkpoint_bytes(
    payload_bytes: bytes,
    selected_round: int,
    input_dimension: int,
    hidden_dims: tuple[int, ...],
) -> DynamicDenseAutoencoder:
    """Load a single checkpoint model from raw safetensors bytes.

    This is the primary entry point for non-personalized (FedAvg / FedProx) scoring.
    It decodes the safetensors and selects the state for the given round.
    """
    states = load_safetensors(payload_bytes)
    return build_model_from_state_dict(
        states,
        f"round_{selected_round}.",
        input_dimension,
        hidden_dims,
    )


def build_personalized_models_from_bytes(
    payload_bytes: bytes,
    selected_round: int,
    client_ids: Sequence[str],
    input_dimension: int,
    hidden_dims: tuple[int, ...],
) -> dict[str, DynamicDenseAutoencoder]:
    """Load per-client personalized models from a safetensors payload.

    Each client's state is stored under the key pattern
    ``round_{selected_round}.client_{client_id}.*``.
    """
    all_states = load_safetensors(payload_bytes)
    return {
        client_id: build_model_from_state_dict(
            all_states,
            f"round_{selected_round}.client_{client_id}.",
            input_dimension,
            hidden_dims,
        )
        for client_id in client_ids
    }
