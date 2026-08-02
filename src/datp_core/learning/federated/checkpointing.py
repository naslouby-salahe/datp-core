"""Federated model checkpoint selection, verification, candidate retention, and persistence."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import polars as pl
import torch
from safetensors.torch import load_file, save_file

from datp_core.domain.enums import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    PopulationIdentityKind,
    ProcessedDataBranch,
)
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    MetricValue,
    RoundNumber,
    checksum_file,
    checksum_text,
)
from datp_core.learning.autoencoder import (
    ModelStateMap,
    ReconstructionAutoencoder,
)
from datp_core.learning.federated.models import (
    CANDIDATE_SUFFIX,
    CheckpointCandidate,
    CheckpointDecision,
    FederatedHistoryAssetName,
    FederatedHistoryColumn,
    FederatedTrainingCoordinate,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
    RoundSnapshot,
    candidate_tensor_name,
)
from datp_core.learning.federated.training import (
    CLIENT_ROUNDS_SCHEMA,
    ROUND_SUMMARY_SCHEMA,
    _validate_schema,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol
from datp_core.protocols.training import (
    fixed_terminal_checkpoint_status,
    require_non_test_checkpoint_selection_inputs,
)
from datp_core.runtime.compute import require_cuda_available


@dataclass(frozen=True, slots=True)
class ReusedGlobalCandidatesRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ReusedPersonalizedCandidatesRequest:
    personalized_coordinate: FederatedTrainingCoordinate
    personalized_output_directory: Path
    global_history_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ReusedFederatedTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


def candidate_set_digest(candidates: Sequence[CheckpointCandidate]) -> Checksum:
    """Canonical candidate-set digest used for publication markers, reuse, and candidate verification."""
    payload = "|".join(
        f"{item.round_number.value}:{item.tensor_checksum.value}:{item.status.value}" for item in candidates
    )
    return checksum_text(f"{checksum_text(payload).value}|{len(candidates)}")


def persist_checkpoint_tensor(state_dict: ModelStateMap, path: Path) -> Checksum:
    path.parent.mkdir(parents=True, exist_ok=True)
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    save_file(cpu_state, str(path))
    return checksum_file(path)


def assert_checkpoint_reload_equality(
    state_dict: ModelStateMap,
    path: Path,
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> None:
    require_cuda_available()
    reloaded_model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    loaded_state = load_file(str(path), device=str(device))
    if set(state_dict.keys()) != set(loaded_state.keys()):
        raise ArtifactIntegrityError(
            "SafeTensors reload tensor names do not match expected parameter keys",
            subject=ContractSubject.ARTIFACT_PATH,
        )
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
    declared = tuple(candidate for candidate in checkpoint_protocol.candidates)
    observed = tuple(item.round_number for item in snapshots)
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


def validate_candidate_coordinates(
    candidates: Sequence[CheckpointCandidate],
    coordinate: FederatedTrainingCoordinate,
    *,
    client: ClientIdentity | None,
    preprocessing_state_set_checksum: Checksum | None = None,
    split_manifest_checksum: Checksum | None = None,
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
        if (
            preprocessing_state_set_checksum is not None
            and candidate.preprocessing_state_set_checksum != preprocessing_state_set_checksum
        ):
            raise ScientificContractError(
                "checkpoint candidate preprocessing checksum mismatch",
                subject=ContractSubject.PREPROCESSING,
            )
        if split_manifest_checksum is not None and candidate.split_manifest_checksum != split_manifest_checksum:
            raise ScientificContractError(
                "checkpoint candidate split checksum mismatch",
                subject=ContractSubject.SPLIT,
            )
        _verify_candidate_file(candidate)


def select_checkpoint(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    coordinate: FederatedTrainingCoordinate,
    client: ClientIdentity | None,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
    preprocessing_state_set_checksum: Checksum | None = None,
    split_manifest_checksum: Checksum | None = None,
) -> CheckpointDecision:
    """Select the primary federated checkpoint under FIXED_TERMINAL_MAXIMUM_ROUND."""
    require_non_test_checkpoint_selection_inputs(
        selection_rule=selection_rule,
        held_out_metrics=held_out_metrics,
        attack_labels_present=attack_labels_present,
        branch_label=ProcessedDataBranch.FEDERATED,
    )
    ordered = tuple(candidates)
    _reject_duplicate_or_missing_candidates(ordered, protocol)
    validate_candidate_coordinates(
        ordered,
        coordinate,
        client=client,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    for candidate in ordered:
        if candidate.status is CheckpointStatus.HISTORICAL_ENDPOINT:
            raise ScientificContractError(
                "historical anchor endpoint status is incompatible with federated candidates",
                subject=candidate.status,
            )

    statused, selected = _statused_candidates(ordered, protocol.maximum_round)
    return CheckpointDecision(
        coordinate=coordinate,
        client=client,
        selected=selected,
        candidates=statused,
        checkpoint_protocol=protocol,
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )


def _statused_candidates(
    ordered: tuple[CheckpointCandidate, ...],
    maximum_round: RoundNumber,
) -> tuple[tuple[CheckpointCandidate, ...], CheckpointCandidate]:
    statused: list[CheckpointCandidate] = []
    selected: CheckpointCandidate | None = None
    for item in ordered:
        status = fixed_terminal_checkpoint_status(item.round_number, maximum_round)
        rebuilt = replace(item, status=status)
        statused.append(rebuilt)
        if status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            selected = rebuilt
    if selected is None:
        raise ArtifactIntegrityError(
            "fixed-terminal selection failed to mark the maximum-round candidate",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )
    return tuple(statused), selected


def reject_centralized_checkpoint(marker_identity: FederatedTrainingCoordinate) -> None:
    raise LeakageError(
        f"centralized checkpoint cannot enter federated scoring or selection ({marker_identity})",
        subject=ContractSubject.CHECKPOINT_CANDIDATES,
    )


def _reject_duplicate_or_missing_candidates(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
) -> None:
    observed = tuple(item.round_number for item in candidates)
    expected = tuple(protocol.candidates)
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
    if candidate.tensor_path.suffix != CANDIDATE_SUFFIX:
        raise ArtifactIntegrityError(
            "federated checkpoints must use SafeTensors serialization",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def federated_training_directory_is_reusable(
    directory: Path,
    candidate_rounds: tuple[RoundNumber, ...],
    expected_digest: Checksum | None = None,
) -> bool:
    complete = directory / FederatedHistoryAssetName.COMPLETE.value
    round_summary = directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    client_rounds = directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value
    device_name = directory / FederatedHistoryAssetName.DEVICE_NAME.value
    if not all(path.is_file() for path in (complete, round_summary, client_rounds, device_name)):
        return False
    if not device_name.read_text(encoding="utf-8").strip():
        return False
    if expected_digest is not None:
        marker_text = complete.read_text(encoding="utf-8").strip()
        if marker_text != expected_digest.value:
            return False
    try:
        round_frame = pl.read_parquet(round_summary)
        _validate_schema(round_frame, ROUND_SUMMARY_SCHEMA)
        client_frame = pl.read_parquet(client_rounds)
        _validate_schema(client_frame, CLIENT_ROUNDS_SCHEMA)
    except (ArtifactIntegrityError, ScientificContractError, Exception):
        return False
    return all((directory / candidate_tensor_name(round_number)).is_file() for round_number in candidate_rounds)


def load_published_device_name(directory: Path) -> str:
    device_path = directory / FederatedHistoryAssetName.DEVICE_NAME.value
    if not device_path.is_file():
        raise ArtifactIntegrityError(
            "reused federated training is missing the published device name",
            subject=ContractSubject.CUDA,
        )
    device_name = device_path.read_text(encoding="utf-8").strip()
    if not device_name:
        raise ArtifactIntegrityError(
            "reused federated training device name is empty",
            subject=ContractSubject.CUDA,
        )
    return device_name


def load_reused_global_candidates(request: ReusedGlobalCandidatesRequest) -> tuple[CheckpointCandidate, ...]:
    col = FederatedHistoryColumn
    round_summary_path = request.directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    if not round_summary_path.is_file():
        raise ArtifactIntegrityError(
            "reused global candidates missing history summary",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    round_frame = pl.read_parquet(round_summary_path)
    _validate_schema(round_frame, ROUND_SUMMARY_SCHEMA)
    loss_by_round = {
        RoundNumber(int(row[col.ROUND_NUMBER.value])): MetricValue(float(row[col.AGGREGATE_LOSS.value]))
        for row in round_frame.iter_rows(named=True)
    }
    candidates: list[CheckpointCandidate] = []
    for candidate_round in request.checkpoint_protocol.candidates:
        path = request.directory / candidate_tensor_name(candidate_round)
        if not path.is_file():
            raise ArtifactIntegrityError("reused checkpoint candidate missing", subject=ContractSubject.ARTIFACT_PATH)
        candidates.append(
            CheckpointCandidate(
                coordinate=request.coordinate,
                round_number=candidate_round,
                client=None,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
                mean_training_loss=loss_by_round[candidate_round],
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                split_manifest_checksum=request.split_manifest_checksum,
            )
        )
    return tuple(candidates)


def load_reused_personalized_candidates(
    request: ReusedPersonalizedCandidatesRequest,
) -> tuple[PersonalizedCandidateSet, ...]:
    personalized_rounds_path = request.global_history_directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    if not personalized_rounds_path.is_file():
        raise ArtifactIntegrityError(
            "reused personalized candidates require published personalized round losses",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    personalized_frame = pl.read_parquet(personalized_rounds_path)
    col = FederatedHistoryColumn
    result: list[PersonalizedCandidateSet] = []
    for client in request.clients:
        candidates: list[CheckpointCandidate] = []
        for candidate_round in request.checkpoint_protocol.candidates:
            path = request.personalized_output_directory / candidate_tensor_name(candidate_round, client)
            if not path.is_file():
                raise ArtifactIntegrityError(
                    "reused personalized checkpoint candidate missing",
                    subject=ContractSubject.ARTIFACT_PATH,
                )
            loss_rows = personalized_frame.filter(
                (pl.col(col.ROUND_NUMBER.value) == candidate_round.value)
                & (pl.col(col.CLIENT_ID.value) == client.client_id)
            )
            if loss_rows.height != 1:
                raise ArtifactIntegrityError(
                    "reused personalized candidate is missing its published local loss",
                    subject=ContractSubject.TRAINING,
                )
            local_loss = MetricValue(float(loss_rows.item(0, col.LOCAL_LOSS.value)))
            candidates.append(
                CheckpointCandidate(
                    coordinate=request.personalized_coordinate,
                    round_number=candidate_round,
                    client=client,
                    tensor_path=path,
                    tensor_checksum=checksum_file(path),
                    mean_training_loss=local_loss,
                    status=CheckpointStatus.CANDIDATE,
                    preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                    split_manifest_checksum=request.split_manifest_checksum,
                )
            )
        result.append(PersonalizedCandidateSet(client=client, candidates=tuple(candidates)))
    return tuple(result)


def rebase_checkpoint_candidates(
    candidates: tuple[CheckpointCandidate, ...],
    directory: Path,
    *,
    client: ClientIdentity | None,
) -> tuple[CheckpointCandidate, ...]:
    """Rebase candidates to target directory, verifying target file existence and exact checksum equality."""
    rebased: list[CheckpointCandidate] = []
    for candidate in candidates:
        path = directory / candidate_tensor_name(candidate.round_number, client)
        if not path.is_file():
            raise ArtifactIntegrityError(
                "rebased target checkpoint tensor does not exist", subject=ContractSubject.ARTIFACT_PATH
            )
        actual_checksum = checksum_file(path)
        if actual_checksum != candidate.tensor_checksum:
            raise ArtifactIntegrityError(
                "rebased target checkpoint tensor checksum mismatch", subject=ContractSubject.ARTIFACT_PATH
            )
        rebased.append(
            replace(
                candidate,
                tensor_path=path,
            )
        )
    return tuple(rebased)


def load_reused_federated_training(
    request: ReusedFederatedTrainingRequest,
) -> tuple[FederatedTrainingResult, tuple[CheckpointCandidate, ...]]:
    from datp_core.learning.federated.training import load_federated_training_history

    history = load_federated_training_history(request.coordinate, request.directory, request.identity_kind)
    candidates = load_reused_global_candidates(
        ReusedGlobalCandidatesRequest(
            coordinate=request.coordinate,
            directory=request.directory,
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    training_result = FederatedTrainingResult(
        coordinate=request.coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=load_published_device_name(request.directory),
        batch_size_used=request.batch_size,
    )
    return training_result, candidates
