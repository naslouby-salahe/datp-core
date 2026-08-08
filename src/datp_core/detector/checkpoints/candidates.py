"""Federated checkpoint tensor persistence and candidate path ownership."""

from collections.abc import Sequence
from dataclasses import replace
from os import replace as atomic_replace
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderStateView, build_autoencoder_for_state
from datp_core.detector.checkpoints.contracts import (
    CheckpointProtocol,
    validate_ordered_checkpoint_inventory,
    validate_persisted_checkpoint_file,
)
from datp_core.detector.training.models import (
    CheckpointCandidate,
    FederatedTrainingCoordinate,
    RoundSnapshot,
)
from datp_core.domain.enums import CheckpointStatus, ContractSubject
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.domain.values.counts import RoundNumber
from datp_core.domain.values.identifiers import SafeTensorFilename
from datp_core.protocols.training import AutoencoderProtocol

_CANDIDATE_PREFIX = "checkpoint_round_"
_CANDIDATE_SUFFIX = ".safetensors"
_PERSONALIZED_INFIX = "_client_"


def candidate_tensor_name(
    round_number: RoundNumber,
    client: ClientIdentity | None = None,
) -> SafeTensorFilename:
    if client is not None:
        return SafeTensorFilename(
            f"{_CANDIDATE_PREFIX}{round_number.value}{_PERSONALIZED_INFIX}{client.client_id}{_CANDIDATE_SUFFIX}"
        )
    return SafeTensorFilename(f"{_CANDIDATE_PREFIX}{round_number.value}{_CANDIDATE_SUFFIX}")


def persist_checkpoint_tensor(
    state_dict: AutoencoderStateView,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> Checksum:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.tmp")
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    save_file(cpu_state, str(staging))
    _assert_checkpoint_reload_equality(cpu_state, staging, autoencoder)
    atomic_replace(staging, path)
    return checksum_file(path)


def _assert_checkpoint_reload_equality(
    cpu_state_dict: dict[str, torch.Tensor],
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> None:
    loaded = load_file(str(path), device="cpu")
    if loaded.keys() != cpu_state_dict.keys():
        raise ArtifactIntegrityError(
            "checkpoint tensor names do not match the expected model state",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    for name, reference in cpu_state_dict.items():
        observed = loaded[name]
        if observed.shape != reference.shape or observed.dtype != reference.dtype:
            raise ArtifactIntegrityError(
                "checkpoint tensor shape or dtype differs from the expected model state",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        if not torch.equal(observed, reference):
            raise ArtifactIntegrityError(
                "checkpoint tensor values differ from the expected model state",
                subject=ContractSubject.ARTIFACT_PATH,
            )
    build_autoencoder_for_state(
        autoencoder,
        loaded,
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
    observed = tuple(snapshot.round_number for snapshot in snapshots)
    if observed != checkpoint_protocol.candidates:
        raise ScientificContractError(
            "checkpoint snapshots must equal the exact ordered protocol candidates",
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
        checkpoint_protocol.candidates,
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
            snapshot.state_dict,
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
    rebased_list = []
    for candidate in candidates:
        new_path = directory / candidate_tensor_name(candidate.round_number, candidate.client)
        validate_persisted_checkpoint_file(new_path, candidate.tensor_checksum)
        rebased_list.append(replace(candidate, tensor_path=new_path))
    return tuple(rebased_list)
