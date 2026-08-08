"""SafeTensors state-dictionary serialization with exact reload validation."""

from os import replace as atomic_replace
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.detector.autoencoder import AutoencoderState, AutoencoderStateView


def dump_state_dict(state: AutoencoderStateView, destination: Path) -> Checksum:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.tmp")
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state.items()}
    save_file(cpu_state, str(staging))
    _assert_exact_reload(cpu_state, staging)
    atomic_replace(staging, destination)
    return checksum_file(destination)


def load_state_dict(path: Path, *, expected_checksum: Checksum | None = None) -> AutoencoderState:
    if expected_checksum is not None and checksum_file(path) != expected_checksum:
        raise ArtifactIntegrityError("SafeTensors checksum mismatch")
    loaded = load_file(str(path), device="cpu")
    return {name: tensor for name, tensor in loaded.items()}


def _assert_exact_reload(reference: AutoencoderStateView, path: Path) -> None:
    observed = load_file(str(path), device="cpu")
    if observed.keys() != reference.keys():
        raise ArtifactIntegrityError("SafeTensors tensor names do not match the source state")
    for name, expected in reference.items():
        actual = observed[name]
        if actual.shape != expected.shape or actual.dtype != expected.dtype:
            raise ArtifactIntegrityError("SafeTensors tensor shape or dtype changed during serialization")
        if not torch.equal(actual, expected):
            raise ArtifactIntegrityError("SafeTensors tensor values changed during serialization")
