"""Centralized checkpoint candidate retention and non-test selection boundary."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.centralized_reference.training import (
    CentralizedModelSnapshot,
    CentralizedTrainingCoordinate,
    CentralizedTrainingResult,
    assert_safetensors_reload,
    model_from_snapshot,
    persist_state_dict_tensors,
)
from datp_core.domain.enums import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    SerializationFormat,
)
from datp_core.domain.errors import (
    ArtifactIntegrityError,
    LeakageError,
    ScientificContractError,
)
from datp_core.domain.values import Checksum, MetricValue, RoundNumber, checksum_file, checksum_text
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol
from datp_core.protocols.training import fixed_terminal_checkpoint_status, require_non_test_checkpoint_selection_inputs
from datp_core.runtime.compute import resolve_cuda_device


class CentralizedCheckpointAssetName(StrEnum):
    CANDIDATE_PREFIX = "checkpoint_round_"
    CANDIDATE_SUFFIX = ".safetensors"
    CANDIDATES_MANIFEST = "checkpoint_candidates.json"
    DECISION = "checkpoint_decision.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class CentralizedCheckpointCandidate:
    coordinate: CentralizedTrainingCoordinate
    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    training_seed_value: int
    autoencoder_widths: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.status not in {
            CheckpointStatus.CANDIDATE,
            CheckpointStatus.STABILITY_EVIDENCE,
            CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        }:
            raise ScientificContractError(
                "centralized checkpoint candidate has an invalid status",
                subject=self.status,
            )
        if self.training_seed_value < 0:
            raise ValueError("training seed value must be non-negative")


@dataclass(frozen=True, slots=True)
class CentralizedCheckpointDecision:
    coordinate: CentralizedTrainingCoordinate
    selected: CentralizedCheckpointCandidate
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    selection_rule: CheckpointSelectionRule
    status: CheckpointStatus

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError("checkpoint decision requires retained candidates")
        selected_rounds = {item.round_number.value for item in self.candidates}
        if self.selected.round_number.value not in selected_rounds:
            raise ScientificContractError(
                "selected checkpoint must be one of the retained candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "centralized checkpoint decision status must be SELECTED_BY_NON_TEST_RULE",
                subject=self.status,
            )
        if self.selection_rule is not CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
            raise ScientificContractError(
                "centralized checkpoint decision must use FIXED_TERMINAL_MAXIMUM_ROUND",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "selected checkpoint must equal the declared maximum round",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "selected candidate status must be SELECTED_BY_NON_TEST_RULE",
                subject=self.selected.status,
            )


@dataclass(frozen=True, slots=True)
class FederatedCheckpointMarker:
    """Structural marker used only to reject federated artifacts at the centralized boundary."""

    identity: str
    tensor_path: Path


def candidate_tensor_name(round_number: RoundNumber) -> str:
    return (
        f"{CentralizedCheckpointAssetName.CANDIDATE_PREFIX}"
        f"{round_number.value}"
        f"{CentralizedCheckpointAssetName.CANDIDATE_SUFFIX}"
    )


def retain_centralized_checkpoint_candidates(
    training_result: CentralizedTrainingResult,
    autoencoder: AutoencoderProtocol,
) -> tuple[CentralizedCheckpointCandidate, ...]:
    """Persist every declared candidate snapshot and return typed candidate records."""
    protocol = training_result.checkpoint_protocol
    snapshots = training_result.candidate_snapshots
    declared = tuple(candidate.value for candidate in protocol.candidates)
    observed = tuple(snapshot.round_number.value for snapshot in snapshots)
    if observed != declared:
        raise ScientificContractError(
            "checkpoint snapshots must match the declared candidate rounds exactly and in order",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    candidates: list[CentralizedCheckpointCandidate] = []
    for snapshot in snapshots:
        path = training_result.model_directory / candidate_tensor_name(snapshot.round_number)
        checksum = persist_state_dict_tensors(snapshot.state_dict, path)
        _verify_candidate_reload(snapshot, path, autoencoder)
        candidates.append(
            CentralizedCheckpointCandidate(
                coordinate=training_result.coordinate,
                round_number=snapshot.round_number,
                tensor_path=path,
                tensor_checksum=checksum,
                mean_training_loss=snapshot.mean_training_loss,
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_checksum=training_result.preprocessing_state_checksum,
                split_manifest_checksum=training_result.split_manifest_checksum,
                training_seed_value=training_result.training_seed.value,
                autoencoder_widths=tuple(autoencoder.widths),
            )
        )
    _reject_duplicate_or_missing_candidates(tuple(candidates), protocol)
    return tuple(candidates)


def select_centralized_checkpoint(
    candidates: Sequence[CentralizedCheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
) -> CentralizedCheckpointDecision:
    """Select the primary centralized checkpoint under FIXED_TERMINAL_MAXIMUM_ROUND.

    Among declared candidates, the primary is always the candidate at
    CheckpointProtocol.maximum_round. Training losses are stability evidence only.
    """
    require_non_test_checkpoint_selection_inputs(
        selection_rule=selection_rule,
        held_out_metrics=held_out_metrics,
        attack_labels_present=attack_labels_present,
        branch_label="centralized",
    )
    ordered = tuple(candidates)
    _reject_duplicate_or_missing_candidates(ordered, protocol)
    for candidate in ordered:
        if candidate.status is CheckpointStatus.HISTORICAL_ENDPOINT:
            raise ScientificContractError(
                "historical federated endpoint status is incompatible with centralized candidates",
                subject=candidate.status,
            )
        _verify_candidate_file(candidate)

    terminal = next(
        (item for item in ordered if item.round_number == protocol.maximum_round),
        None,
    )
    if terminal is None:
        raise ArtifactIntegrityError(
            "declared maximum-round checkpoint candidate is missing",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )

    statused, selected = _statused_candidates(ordered, protocol.maximum_round)
    return CentralizedCheckpointDecision(
        coordinate=selected.coordinate,
        selected=selected,
        candidates=statused,
        checkpoint_protocol=protocol,
        selection_rule=selection_rule,
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )


def _statused_candidates(
    ordered: tuple[CentralizedCheckpointCandidate, ...],
    maximum_round: RoundNumber,
) -> tuple[tuple[CentralizedCheckpointCandidate, ...], CentralizedCheckpointCandidate]:
    statused: list[CentralizedCheckpointCandidate] = []
    selected: CentralizedCheckpointCandidate | None = None
    for item in ordered:
        status = fixed_terminal_checkpoint_status(item.round_number, maximum_round)
        rebuilt = CentralizedCheckpointCandidate(
            coordinate=item.coordinate,
            round_number=item.round_number,
            tensor_path=item.tensor_path,
            tensor_checksum=item.tensor_checksum,
            mean_training_loss=item.mean_training_loss,
            status=status,
            preprocessing_state_checksum=item.preprocessing_state_checksum,
            split_manifest_checksum=item.split_manifest_checksum,
            training_seed_value=item.training_seed_value,
            autoencoder_widths=item.autoencoder_widths,
        )
        statused.append(rebuilt)
        if status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            selected = rebuilt
    if selected is None:
        raise ArtifactIntegrityError(
            "fixed-terminal selection failed to mark the maximum-round candidate",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )
    return tuple(statused), selected


def reject_federated_checkpoint(marker: FederatedCheckpointMarker) -> None:
    raise LeakageError(
        f"federated checkpoint cannot enter centralized scoring or selection ({marker.identity})",
        subject=ContractSubject.CHECKPOINT_CANDIDATES,
    )


def validate_candidate_coordinates(
    candidates: Sequence[CentralizedCheckpointCandidate],
    coordinate: CentralizedTrainingCoordinate,
    *,
    preprocessing_checksum: Checksum,
    split_checksum: Checksum,
    training_seed_value: int,
) -> None:
    for candidate in candidates:
        if candidate.coordinate != coordinate:
            raise ScientificContractError(
                "checkpoint candidate coordinate mismatch", subject=ContractSubject.COORDINATE
            )
        if candidate.preprocessing_state_checksum != preprocessing_checksum:
            raise ScientificContractError(
                "checkpoint candidate preprocessing checksum mismatch",
                subject=ContractSubject.PREPROCESSING,
            )
        if candidate.split_manifest_checksum != split_checksum:
            raise ScientificContractError(
                "checkpoint candidate split checksum mismatch",
                subject=ContractSubject.SPLIT,
            )
        if candidate.training_seed_value != training_seed_value:
            raise ScientificContractError(
                "checkpoint candidate training seed mismatch",
                subject=ContractSubject.SEED,
            )


def candidate_set_checksum(candidates: Sequence[CentralizedCheckpointCandidate]) -> Checksum:
    payload = "|".join(
        f"{item.round_number.value}:{item.tensor_checksum.value}:{item.status.value}" for item in candidates
    )
    return checksum_text(payload)


def _reject_duplicate_or_missing_candidates(
    candidates: Sequence[CentralizedCheckpointCandidate],
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


def _verify_candidate_file(candidate: CentralizedCheckpointCandidate) -> None:
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
    suffix = f".{SerializationFormat.SAFETENSORS.value}"
    if candidate.tensor_path.suffix != suffix:
        raise ArtifactIntegrityError(
            "centralized checkpoints must use SafeTensors serialization",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _verify_candidate_reload(
    snapshot: CentralizedModelSnapshot,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> None:
    device = resolve_cuda_device()
    model = model_from_snapshot(snapshot, autoencoder, device)
    assert_safetensors_reload(model, path, device)
