"""Federated checkpoint tensor persistence and candidate path ownership."""

from collections.abc import Sequence
from dataclasses import replace
from os import replace as atomic_replace
from pathlib import Path

import torch

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.safetensors import (
    load_state_dict_tensors,
    save_state_dict_tensors,
)
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import CheckpointStatus, ContractSubject, SafeTensorFilename
from datp_core.core.numeric import RoundNumber
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState, build_autoencoder_for_state
from datp_core.detector.checkpoints.contracts import (
    CheckpointProtocol,
    realized_candidate_rounds,
    validate_ordered_checkpoint_inventory,
    validate_persisted_checkpoint_file,
)
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.models import (
    CheckpointCandidate,
    FederatedTrainingCoordinate,
    RoundSnapshot,
)

_CANDIDATE_PREFIX = "checkpoint_round_"
_CANDIDATE_SUFFIX = ".safetensors"
_PERSONALIZED_INFIX = "_client_"


def candidate_tensor_name(
    round_number: RoundNumber,
    client: ClientIdentity | None = None,
) -> SafeTensorFilename:
    if client is not None:
        return SafeTensorFilename(
            f"{_CANDIDATE_PREFIX}{round_number.value}{_PERSONALIZED_INFIX}{client.client_id.value}{_CANDIDATE_SUFFIX}"
        )
    return SafeTensorFilename(f"{_CANDIDATE_PREFIX}{round_number.value}{_CANDIDATE_SUFFIX}")


def persist_checkpoint_tensor(
    model_state: AutoencoderModelState,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> Checksum:
    staging = path.with_name(f".{path.name}.tmp")
    cpu_model_state = model_state.on_cpu_with_contiguous_tensors()
    checksum = save_state_dict_tensors(cpu_model_state.to_torch_state_dict(), staging)
    _assert_checkpoint_reload_equality(cpu_model_state, staging, autoencoder)
    atomic_replace(staging, path)
    return checksum


def _assert_checkpoint_reload_equality(
    expected_model_state: AutoencoderModelState,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> None:
    loaded_model_state = AutoencoderModelState.from_torch_state_dict(load_state_dict_tensors(path, torch.device("cpu")))
    if not loaded_model_state.is_equivalent_to(expected_model_state):
        raise ArtifactIntegrityError(
            ErrorMessage("checkpoint tensor values differ from the expected model state"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    build_autoencoder_for_state(
        autoencoder,
        loaded_model_state,
        device=torch.device("cpu"),
    )


def retain_checkpoint_candidates(
    coordinate: FederatedTrainingCoordinate,
    snapshots: Sequence[RoundSnapshot],
    *,
    checkpoint_protocol: CheckpointProtocol,
    autoencoder: AutoencoderProtocol,
    output_directory: Path,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    client: ClientIdentity | None,
) -> tuple[CheckpointCandidate, ...]:
    if not snapshots:
        raise ScientificContractError(
            ErrorMessage("checkpoint retention requires snapshots"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    observed = tuple(snapshot.round_number for snapshot in snapshots)
    realized = realized_candidate_rounds(checkpoint_protocol, observed[-1])
    if observed != realized:
        raise ScientificContractError(
            ErrorMessage("checkpoint snapshots must equal the realized protocol candidates"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    candidates = tuple(
        _persist_candidate(
            coordinate=coordinate,
            snapshot=snapshot,
            autoencoder=autoencoder,
            output_directory=output_directory,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
            client=client,
        )
        for snapshot in snapshots
    )
    return validate_ordered_checkpoint_inventory(
        candidates,
        realized,
    )


def _persist_candidate(
    *,
    coordinate: FederatedTrainingCoordinate,
    snapshot: RoundSnapshot,
    autoencoder: AutoencoderProtocol,
    output_directory: Path,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    client: ClientIdentity | None,
) -> CheckpointCandidate:
    path = output_directory / candidate_tensor_name(
        snapshot.round_number,
        client,
    )
    return CheckpointCandidate(
        coordinate=coordinate,
        round_number=snapshot.round_number,
        client=client,
        tensor_path=path,
        tensor_checksum=persist_checkpoint_tensor(
            snapshot.model_state,
            path,
            autoencoder,
        ),
        mean_training_loss=snapshot.mean_training_loss,
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )


def rebase_checkpoint_candidates(
    candidates: Sequence[CheckpointCandidate],
    directory: Path,
) -> tuple[CheckpointCandidate, ...]:
    rebased_list: list[CheckpointCandidate] = []
    for candidate in candidates:
        new_path = directory / candidate_tensor_name(candidate.round_number, candidate.client)
        validate_persisted_checkpoint_file(new_path, candidate.tensor_checksum)
        rebased_list.append(replace(candidate, tensor_path=new_path))
    return tuple(rebased_list)
