"""Persist federated and centralized checkpoint candidate tensors."""

from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.safetensors import dump_state_dict
from datp_core.core.identifiers import CheckpointStatus, SafeTensorFilename
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.checkpoints.contracts import (
    CHECKPOINT_PROTOCOL,
    CentralizedCheckpointCandidate,
    CheckpointCandidate,
    validate_ordered_checkpoint_inventory,
)
from datp_core.detector.training.centralized import CentralizedTrainingResult
from datp_core.detector.training.common import FederatedTrainingResult, RoundSnapshot
from datp_core.detector.training.contracts import AutoencoderProtocol


def checkpoint_tensor_name(round_number, client: ClientIdentity | None = None) -> SafeTensorFilename:
    suffix = f"_client_{client.client_id}" if client is not None else ""
    return SafeTensorFilename(f"checkpoint_round_{round_number.value}{suffix}.safetensors")


def persist_federated_candidates(
    result: FederatedTrainingResult,
    *,
    output_directory: Path,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    client: ClientIdentity | None = None,
) -> tuple[CheckpointCandidate, ...]:
    candidates = tuple(
        _persist_federated_snapshot(
            result=result,
            snapshot=snapshot,
            output_directory=output_directory,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
            client=client,
        )
        for snapshot in result.snapshots
    )
    return validate_ordered_checkpoint_inventory(candidates, CHECKPOINT_PROTOCOL.candidates)


def persist_centralized_candidates(
    result: CentralizedTrainingResult,
    *,
    output_directory: Path,
    preprocessing_state_checksum: Checksum,
    split_manifest_checksum: Checksum,
    autoencoder: AutoencoderProtocol,
) -> tuple[CentralizedCheckpointCandidate, ...]:
    candidates = tuple(
        _persist_centralized_snapshot(
            result=result,
            snapshot=snapshot,
            output_directory=output_directory,
            preprocessing_state_checksum=preprocessing_state_checksum,
            split_manifest_checksum=split_manifest_checksum,
            autoencoder=autoencoder,
        )
        for snapshot in result.snapshots
    )
    return validate_ordered_checkpoint_inventory(candidates, CHECKPOINT_PROTOCOL.candidates)


def _persist_federated_snapshot(
    *,
    result: FederatedTrainingResult,
    snapshot: RoundSnapshot,
    output_directory: Path,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    client: ClientIdentity | None,
) -> CheckpointCandidate:
    path = output_directory / checkpoint_tensor_name(snapshot.round_number, client)
    return CheckpointCandidate(
        coordinate=result.coordinate,
        round_number=snapshot.round_number,
        tensor_path=path,
        tensor_checksum=dump_state_dict(snapshot.state_dict, path),
        mean_training_loss=snapshot.mean_training_loss,
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
        client=client,
    )


def _persist_centralized_snapshot(
    *,
    result: CentralizedTrainingResult,
    snapshot: RoundSnapshot,
    output_directory: Path,
    preprocessing_state_checksum: Checksum,
    split_manifest_checksum: Checksum,
    autoencoder: AutoencoderProtocol,
) -> CentralizedCheckpointCandidate:
    path = output_directory / checkpoint_tensor_name(snapshot.round_number)
    return CentralizedCheckpointCandidate(
        coordinate=result.coordinate,
        round_number=snapshot.round_number,
        tensor_path=path,
        tensor_checksum=dump_state_dict(snapshot.state_dict, path),
        mean_training_loss=snapshot.mean_training_loss,
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_checksum=preprocessing_state_checksum,
        split_manifest_checksum=split_manifest_checksum,
        training_seed=result.coordinate.training_seed,
        autoencoder_widths=autoencoder.widths,
    )
