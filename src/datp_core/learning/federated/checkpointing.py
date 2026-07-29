"""Federated checkpoint candidate persistence and FIXED_TERMINAL_MAXIMUM_ROUND selection."""

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from datp_core.domain.enums import CheckpointSelectionRule, CheckpointStatus, ContractSubject
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, RoundNumber, checksum_file, checksum_text
from datp_core.learning.autoencoder import FederatedAutoencoder
from datp_core.learning.federated.models import CheckpointCandidate, CheckpointDecision, FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol
from datp_core.runtime.compute import require_cuda_available


class FederatedCheckpointAssetName(StrEnum):
    CANDIDATE_PREFIX = "checkpoint_round_"
    CANDIDATE_SUFFIX = ".safetensors"
    PERSONALIZED_INFIX = "_client_"
    COMPLETE = "COMPLETE"


class RoundSnapshot:
    """In-memory candidate-round state prior to persistence. Not a public dataclass."""

    __slots__ = ("round_number", "state_dict", "mean_training_loss")

    def __init__(
        self,
        round_number: RoundNumber,
        state_dict: dict[str, torch.Tensor],
        mean_training_loss: MetricValue,
    ) -> None:
        self.round_number = round_number
        self.state_dict = state_dict
        self.mean_training_loss = mean_training_loss


def candidate_tensor_name(round_number: RoundNumber, client: ClientIdentity | None = None) -> str:
    base = f"{FederatedCheckpointAssetName.CANDIDATE_PREFIX}{round_number.value}"
    if client is not None:
        base = f"{base}{FederatedCheckpointAssetName.PERSONALIZED_INFIX}{client.client_id}"
    return f"{base}{FederatedCheckpointAssetName.CANDIDATE_SUFFIX}"


def persist_checkpoint_tensor(state_dict: dict[str, torch.Tensor], path: Path) -> Checksum:
    path.parent.mkdir(parents=True, exist_ok=True)
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    save_file(cpu_state, str(path))
    return checksum_file(path)


def assert_checkpoint_reload_equality(
    state_dict: dict[str, torch.Tensor],
    path: Path,
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> None:
    require_cuda_available()
    reloaded_model = FederatedAutoencoder(autoencoder.widths).to(device)
    loaded_state = load_file(str(path), device=str(device))
    reloaded_model.load_state_dict(loaded_state, strict=True)
    for name, tensor in state_dict.items():
        reference = tensor.detach().to(device)
        if not torch.equal(reference, loaded_state[name]):
            raise ArtifactIntegrityError(
                "SafeTensors reload does not match saved federated checkpoint weights",
                subject=ContractSubject.ARTIFACT_PATH,
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
    device: torch.device,
) -> tuple[CheckpointCandidate, ...]:
    """Persist every declared candidate round and return typed candidate records."""
    declared = tuple(candidate.value for candidate in checkpoint_protocol.candidates)
    observed = tuple(item.round_number.value for item in snapshots)
    if observed != declared:
        raise ScientificContractError(
            "checkpoint snapshots must match the declared candidate rounds exactly and in order",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    candidates: list[CheckpointCandidate] = []
    for snapshot in snapshots:
        path = output_directory / candidate_tensor_name(snapshot.round_number, client)
        checksum = persist_checkpoint_tensor(snapshot.state_dict, path)
        assert_checkpoint_reload_equality(snapshot.state_dict, path, autoencoder, device)
        candidates.append(
            CheckpointCandidate(
                coordinate=coordinate,
                round_number=snapshot.round_number,
                client=client,
                tensor_path=path,
                tensor_checksum=checksum,
                mean_training_loss=snapshot.mean_training_loss,
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_set_checksum=preprocessing_state_set_checksum,
                split_manifest_checksum=split_manifest_checksum,
            )
        )
    _reject_duplicate_or_missing_candidates(tuple(candidates), checkpoint_protocol)
    return tuple(candidates)


def select_checkpoint(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    coordinate: FederatedTrainingCoordinate,
    client: ClientIdentity | None,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
) -> CheckpointDecision:
    """Select the primary federated checkpoint under FIXED_TERMINAL_MAXIMUM_ROUND.

    Among declared candidates, the primary is always the candidate at
    CheckpointProtocol.maximum_round. Training losses are stability evidence only.
    """
    if held_out_metrics is not None:
        raise LeakageError(
            "held-out evaluation outcomes cannot influence federated checkpoint selection",
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if attack_labels_present:
        raise LeakageError(
            "attack labels cannot influence federated checkpoint selection",
            subject=ContractSubject.ATTACK_LABELS,
        )
    if selection_rule is not CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
        raise ScientificContractError(
            "unsupported federated checkpoint selection rule",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )
    ordered = tuple(candidates)
    _reject_duplicate_or_missing_candidates(ordered, protocol)
    for candidate in ordered:
        if candidate.status is CheckpointStatus.HISTORICAL_ENDPOINT:
            raise ScientificContractError(
                "historical anchor endpoint status is incompatible with federated candidates",
                subject=candidate.status,
            )
        _verify_candidate_file(candidate)

    terminal = next((item for item in ordered if item.round_number == protocol.maximum_round), None)
    if terminal is None:
        raise ArtifactIntegrityError(
            "declared maximum-round checkpoint candidate is missing",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )

    statused: list[CheckpointCandidate] = []
    selected: CheckpointCandidate | None = None
    for item in ordered:
        status = (
            CheckpointStatus.SELECTED_BY_NON_TEST_RULE
            if item.round_number == protocol.maximum_round
            else CheckpointStatus.STABILITY_EVIDENCE
        )
        rebuilt = CheckpointCandidate(
            coordinate=item.coordinate,
            round_number=item.round_number,
            client=item.client,
            tensor_path=item.tensor_path,
            tensor_checksum=item.tensor_checksum,
            mean_training_loss=item.mean_training_loss,
            status=status,
            preprocessing_state_set_checksum=item.preprocessing_state_set_checksum,
            split_manifest_checksum=item.split_manifest_checksum,
        )
        statused.append(rebuilt)
        if status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            selected = rebuilt
    if selected is None:
        raise ArtifactIntegrityError(
            "fixed-terminal selection failed to mark the maximum-round candidate",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )
    return CheckpointDecision(
        coordinate=coordinate,
        client=client,
        selected=selected,
        candidates=tuple(statused),
        checkpoint_protocol=protocol,
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )


def reject_centralized_checkpoint(marker_identity: str) -> None:
    raise LeakageError(
        f"centralized checkpoint cannot enter federated scoring or selection ({marker_identity})",
        subject=ContractSubject.CHECKPOINT_CANDIDATES,
    )


def validate_candidate_coordinates(
    candidates: Sequence[CheckpointCandidate],
    coordinate: FederatedTrainingCoordinate,
    *,
    client: ClientIdentity | None,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
) -> None:
    for candidate in candidates:
        if candidate.coordinate != coordinate:
            raise ScientificContractError(
                "checkpoint candidate coordinate mismatch", subject=ContractSubject.COORDINATE
            )
        if candidate.client != client:
            raise ScientificContractError(
                "checkpoint candidate client identity mismatch", subject=ContractSubject.CLIENT_IDENTITY
            )
        if candidate.preprocessing_state_set_checksum != preprocessing_state_set_checksum:
            raise ScientificContractError(
                "checkpoint candidate preprocessing checksum mismatch",
                subject=ContractSubject.PREPROCESSING,
            )
        if candidate.split_manifest_checksum != split_manifest_checksum:
            raise ScientificContractError(
                "checkpoint candidate split checksum mismatch",
                subject=ContractSubject.SPLIT,
            )


def candidate_set_checksum(candidates: Sequence[CheckpointCandidate]) -> Checksum:
    payload = "|".join(
        f"{item.round_number.value}:{item.tensor_checksum.value}:{item.status.value}" for item in candidates
    )
    return checksum_text(payload)


def _reject_duplicate_or_missing_candidates(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
) -> None:
    observed = tuple(item.round_number.value for item in candidates)
    expected = tuple(item.value for item in protocol.candidates)
    if observed != expected:
        raise ArtifactIntegrityError(
            "checkpoint candidate rounds must equal the declared ordered protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    if len(set(observed)) != len(observed):
        raise ArtifactIntegrityError(
            "duplicate checkpoint candidates are forbidden", subject=ContractSubject.CHECKPOINT_CANDIDATES
        )
    paths = tuple(item.tensor_path for item in candidates)
    if len(set(paths)) != len(paths):
        raise ArtifactIntegrityError(
            "checkpoint candidate paths must be unique", subject=ContractSubject.CHECKPOINT_CANDIDATES
        )


def _verify_candidate_file(candidate: CheckpointCandidate) -> None:
    if not candidate.tensor_path.is_file():
        raise ArtifactIntegrityError(
            "checkpoint candidate tensor file is missing", subject=ContractSubject.ARTIFACT_PATH
        )
    actual = checksum_file(candidate.tensor_path)
    if actual != candidate.tensor_checksum:
        raise ArtifactIntegrityError(
            "checkpoint candidate checksum mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if candidate.tensor_path.suffix != FederatedCheckpointAssetName.CANDIDATE_SUFFIX:
        raise ArtifactIntegrityError(
            "federated checkpoints must use SafeTensors serialization",
            subject=ContractSubject.ARTIFACT_PATH,
        )
