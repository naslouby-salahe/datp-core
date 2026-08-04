"""Federated checkpoint tensor persistence, manifests, completion, and trusted reload."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from os import replace as atomic_replace
from pathlib import Path

import torch
from pydantic import ValidationError
from safetensors.torch import load_file, save_file

from datp_core.artifacts.serialization import canonical_checksum, serialize_json_model
from datp_core.domain.enums import CheckpointStatus, ContractSubject, TrainingModelId
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientPathToken,
    ManifestSchemaVersion,
    MetricValue,
    ModelCoefficientValue,
    RoundNumber,
    SafeTensorFilename,
    checksum_file,
)
from datp_core.learning.autoencoder import AutoencoderStateView, build_autoencoder_for_state
from datp_core.learning.federated.checkpoints.documents import CandidateManifest, CandidateManifestEntry
from datp_core.learning.federated.checkpoints.history import (
    history_frames,
    read_parquet,
    validate_personalized_history,
    validate_round_summary,
)
from datp_core.learning.federated.checkpoints.identities import (
    CandidateManifestKind,
    FederatedHistoryAssetName,
    FederatedHistoryColumn,
)
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    FederatedTrainingCoordinate,
    PersonalizedCandidateSet,
    PersonalizedSnapshotSet,
    RoundSnapshot,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol

_CANDIDATE_PREFIX = "checkpoint_round_"
_CANDIDATE_SUFFIX = ".safetensors"
_PERSONALIZED_INFIX = "_client_"
_MANIFEST_SCHEMA_VERSION = ManifestSchemaVersion(1)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusedGlobalCandidatesRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusedPersonalizedCandidatesRequest:
    personalized_coordinate: FederatedTrainingCoordinate
    personalized_output_directory: Path
    global_history_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationFileChecksum:
    name: str
    checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class RoundLoss:
    round_number: RoundNumber
    loss: MetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientRoundLoss:
    client_id: str
    round_number: RoundNumber
    loss: MetricValue


def candidate_tensor_name(
    round_number: RoundNumber,
    client: ClientIdentity | None = None,
) -> SafeTensorFilename:
    base = f"{_CANDIDATE_PREFIX}{round_number.value}"
    if client is not None:
        base = f"{base}{_PERSONALIZED_INFIX}{client.client_id}"
    return SafeTensorFilename(f"{base}{_CANDIDATE_SUFFIX}")


def persist_checkpoint_tensor(
    state_dict: AutoencoderStateView,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> Checksum:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.tmp")
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    save_file(cpu_state, str(staging))
    _assert_checkpoint_reload_equality(state_dict, staging, autoencoder)
    atomic_replace(staging, path)
    return checksum_file(path)


def _assert_checkpoint_reload_equality(
    state_dict: AutoencoderStateView,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> None:
    loaded = load_file(str(path), device="cpu")
    if loaded.keys() != state_dict.keys():
        raise ArtifactIntegrityError(
            "checkpoint tensor names do not match the expected model state",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    for name, expected in state_dict.items():
        observed = loaded[name]
        reference = expected.detach().cpu().contiguous()
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
    build_autoencoder_for_state(autoencoder, loaded, device=torch.device("cpu"))


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
    validate_candidate_rounds_and_paths(candidates, checkpoint_protocol)
    return candidates


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
    path = output_directory / candidate_tensor_name(snapshot.round_number, client)
    return CheckpointCandidate(
        coordinate=coordinate,
        round_number=snapshot.round_number,
        client=client,
        tensor_path=path,
        tensor_checksum=persist_checkpoint_tensor(snapshot.state_dict, path, autoencoder),
        mean_training_loss=snapshot.mean_training_loss,
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )


def build_manifest(
    *,
    kind: CandidateManifestKind,
    coordinate: FederatedTrainingCoordinate,
    candidates: Sequence[CheckpointCandidate],
    checkpoint_protocol: CheckpointProtocol,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    linked_personalized_digest: Checksum | None = None,
) -> CandidateManifest:
    return CandidateManifest(
        schema_version=_MANIFEST_SCHEMA_VERSION,
        kind=kind,
        coordinate_population=coordinate.population,
        coordinate_training_seed=coordinate.training_seed,
        coordinate_split_protocol=coordinate.split_protocol,
        coordinate_preprocessing_identity=coordinate.preprocessing_identity,
        coordinate_model=coordinate.model,
        coordinate_model_coefficient=(
            ModelCoefficientValue(coordinate.model_coefficient.value)
            if coordinate.model_coefficient is not None
            else None
        ),
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
        checkpoint_rounds=checkpoint_protocol.candidates,
        autoencoder_widths=tuple(autoencoder.widths),
        batch_size=batch_size,
        linked_personalized_digest=linked_personalized_digest,
        entries=tuple(
            CandidateManifestEntry(
                round_number=candidate.round_number,
                client_id=ClientPathToken(candidate.client.client_id) if candidate.client is not None else None,
                tensor_name=SafeTensorFilename(candidate.tensor_path.name),
                tensor_checksum=candidate.tensor_checksum,
            )
            for candidate in candidates
        ),
    )


def write_manifest(directory: Path, manifest: CandidateManifest) -> None:
    serialize_json_model(manifest, directory / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value)


def load_manifest(directory: Path) -> CandidateManifest:
    path = directory / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value
    if not path.is_file():
        raise ArtifactIntegrityError("candidate manifest is missing", subject=ContractSubject.ARTIFACT_PATH)
    try:
        manifest = CandidateManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ArtifactIntegrityError(
            "candidate manifest is unreadable or invalid",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error
    if manifest.schema_version != _MANIFEST_SCHEMA_VERSION:
        raise ArtifactIntegrityError(
            "candidate manifest schema version is unsupported",
            subject=ContractSubject.SCHEMA,
        )
    return manifest


def expected_publication_files(manifest: CandidateManifest, *, include_history: bool) -> tuple[str, ...]:
    names = (
        FederatedHistoryAssetName.CANDIDATE_MANIFEST.value,
        *(entry.tensor_name for entry in manifest.entries),
    )
    if not include_history:
        return tuple(sorted(names))
    history_names = (
        FederatedHistoryAssetName.ROUND_SUMMARY.value,
        FederatedHistoryAssetName.CLIENT_ROUNDS.value,
        FederatedHistoryAssetName.DEVICE_NAME.value,
    )
    personalized = (
        (FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value,)
        if manifest.coordinate_model is TrainingModelId.DITTO_GLOBAL_AUTOENCODER
        else ()
    )
    return tuple(sorted((*names, *history_names, *personalized)))


def publication_digest(directory: Path, expected_files: Sequence[str]) -> Checksum:
    projection = tuple(
        PublicationFileChecksum(name=name, checksum=checksum_file(directory / name))
        for name in sorted(expected_files)
    )
    return canonical_checksum(projection)


def write_completion(directory: Path, manifest: CandidateManifest, *, include_history: bool) -> Checksum:
    digest = publication_digest(directory, expected_publication_files(manifest, include_history=include_history))
    (directory / FederatedHistoryAssetName.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return digest


def verify_completion(directory: Path, manifest: CandidateManifest, *, include_history: bool) -> Checksum:
    expected_without_complete = expected_publication_files(manifest, include_history=include_history)
    expected_all = frozenset((*expected_without_complete, FederatedHistoryAssetName.COMPLETE.value))
    actual_files = frozenset(path.name for path in directory.iterdir() if path.is_file())
    if actual_files != expected_all:
        raise ArtifactIntegrityError(
            "publication files do not match the exact declared artifact set",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    complete = directory / FederatedHistoryAssetName.COMPLETE.value
    try:
        stored = Checksum(complete.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError, ValueError) as error:
        raise ArtifactIntegrityError(
            "completion marker is unreadable or invalid",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error
    recomputed = publication_digest(directory, expected_without_complete)
    if stored != recomputed:
        raise ArtifactIntegrityError(
            "completion marker does not match the current publication",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return recomputed


def validate_candidate_rounds_and_paths(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
) -> None:
    if tuple(candidate.round_number for candidate in candidates) != protocol.candidates:
        raise ArtifactIntegrityError(
            "checkpoint candidate rounds do not match the protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    paths = tuple(candidate.tensor_path for candidate in candidates)
    if len(frozenset(paths)) != len(paths):
        raise ArtifactIntegrityError(
            "checkpoint candidate paths must be unique",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def verify_candidate_file(candidate: CheckpointCandidate) -> None:
    if candidate.tensor_path.suffix != _CANDIDATE_SUFFIX:
        raise ArtifactIntegrityError(
            "federated checkpoints must use SafeTensors",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if not candidate.tensor_path.is_file():
        raise ArtifactIntegrityError("checkpoint candidate file is missing", subject=ContractSubject.ARTIFACT_PATH)
    if checksum_file(candidate.tensor_path) != candidate.tensor_checksum:
        raise ArtifactIntegrityError("checkpoint candidate checksum mismatch", subject=ContractSubject.ARTIFACT_PATH)


def rebase_checkpoint_candidates(
    candidates: Sequence[CheckpointCandidate],
    directory: Path,
) -> tuple[CheckpointCandidate, ...]:
    rebased = tuple(
        replace(
            candidate,
            tensor_path=directory / candidate_tensor_name(candidate.round_number, candidate.client),
        )
        for candidate in candidates
    )
    for original, candidate in zip(candidates, rebased, strict=True):
        if not candidate.tensor_path.is_file():
            raise ArtifactIntegrityError("rebased checkpoint file is missing", subject=ContractSubject.ARTIFACT_PATH)
        if checksum_file(candidate.tensor_path) != original.tensor_checksum:
            raise ArtifactIntegrityError(
                "rebased checkpoint checksum does not match the original candidate",
                subject=ContractSubject.ARTIFACT_PATH,
            )
    return rebased


def validate_manifest(
    manifest: CandidateManifest,
    *,
    kind: CandidateManifestKind,
    coordinate: FederatedTrainingCoordinate,
    checkpoint_protocol: CheckpointProtocol,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
) -> None:
    expected_coefficient = (
        ModelCoefficientValue(coordinate.model_coefficient.value)
        if coordinate.model_coefficient is not None
        else None
    )
    coordinate_matches = (
        manifest.coordinate_population == coordinate.population
        and manifest.coordinate_training_seed == coordinate.training_seed
        and manifest.coordinate_split_protocol == coordinate.split_protocol
        and manifest.coordinate_preprocessing_identity == coordinate.preprocessing_identity
        and manifest.coordinate_model == coordinate.model
        and manifest.coordinate_model_coefficient == expected_coefficient
    )
    if not coordinate_matches:
        raise ArtifactIntegrityError(
            "candidate manifest coordinate does not match the requested experiment",
            subject=ContractSubject.COORDINATE,
        )
    checks = (
        (manifest.kind is kind, "candidate manifest kind mismatch", ContractSubject.ARTIFACT_PATH),
        (
            manifest.preprocessing_state_set_checksum == preprocessing_state_set_checksum,
            "candidate manifest preprocessing checksum mismatch",
            ContractSubject.PREPROCESSING,
        ),
        (
            manifest.split_manifest_checksum == split_manifest_checksum,
            "candidate manifest split checksum mismatch",
            ContractSubject.SPLIT,
        ),
        (
            manifest.checkpoint_rounds == checkpoint_protocol.candidates,
            "candidate manifest rounds do not match the checkpoint protocol",
            ContractSubject.CHECKPOINT_CANDIDATES,
        ),
        (
            manifest.autoencoder_widths == tuple(autoencoder.widths),
            "candidate manifest autoencoder architecture mismatch",
            ContractSubject.WIDTHS,
        ),
        (
            manifest.batch_size == batch_size,
            "candidate manifest batch size mismatch",
            ContractSubject.BATCH_SIZE,
        ),
    )
    for valid, message, subject in checks:
        if not valid:
            raise ArtifactIntegrityError(message, subject=subject)


def validated_global_manifest(request: ReusedGlobalCandidatesRequest) -> CandidateManifest:
    manifest = load_manifest(request.directory)
    validate_manifest(
        manifest,
        kind=CandidateManifestKind.GLOBAL,
        coordinate=request.coordinate,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    verify_completion(request.directory, manifest, include_history=True)
    expected_entries = tuple(
        (round_number, None, candidate_tensor_name(round_number))
        for round_number in request.checkpoint_protocol.candidates
    )
    observed_entries = tuple((entry.round_number, entry.client_id, entry.tensor_name) for entry in manifest.entries)
    if observed_entries != expected_entries:
        raise ArtifactIntegrityError(
            "global candidate manifest entries are incomplete, duplicated, or out of order",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return manifest


def load_reused_global_candidates(request: ReusedGlobalCandidatesRequest) -> tuple[CheckpointCandidate, ...]:
    manifest = validated_global_manifest(request)
    round_frame, _, _ = history_frames(request.directory)
    expected_rounds = tuple(
        RoundNumber(value) for value in range(1, request.checkpoint_protocol.maximum_round.value + 1)
    )
    validate_round_summary(round_frame, expected_rounds)
    losses = tuple(
        RoundLoss(
            round_number=RoundNumber(int(round_number)),
            loss=MetricValue(float(loss)),
        )
        for round_number, loss in round_frame.select(
            (
                FederatedHistoryColumn.ROUND_NUMBER.value,
                FederatedHistoryColumn.AGGREGATE_LOSS.value,
            )
        ).iter_rows()
    )
    return tuple(_global_candidate(request, entry, losses) for entry in manifest.entries)


def _global_candidate(
    request: ReusedGlobalCandidatesRequest,
    entry: CandidateManifestEntry,
    losses: tuple[RoundLoss, ...],
) -> CheckpointCandidate:
    path = request.directory / entry.tensor_name
    actual = checksum_file(path)
    if actual != entry.tensor_checksum:
        raise ArtifactIntegrityError(
            "reused global checkpoint checksum mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    matching = tuple(item.loss for item in losses if item.round_number == entry.round_number)
    if len(matching) != 1:
        raise ArtifactIntegrityError(
            "global checkpoint requires exactly one matching round loss",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return CheckpointCandidate(
        coordinate=request.coordinate,
        round_number=entry.round_number,
        client=None,
        tensor_path=path,
        tensor_checksum=actual,
        mean_training_loss=matching[0],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


def validated_personalized_manifest(request: ReusedPersonalizedCandidatesRequest) -> CandidateManifest:
    manifest = load_manifest(request.personalized_output_directory)
    validate_manifest(
        manifest,
        kind=CandidateManifestKind.PERSONALIZED,
        coordinate=request.personalized_coordinate,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    verify_completion(request.personalized_output_directory, manifest, include_history=False)
    expected_entries = tuple(
        (round_number, client.client_id, candidate_tensor_name(round_number, client))
        for client in request.clients
        for round_number in request.checkpoint_protocol.candidates
    )
    observed_entries = tuple((entry.round_number, entry.client_id, entry.tensor_name) for entry in manifest.entries)
    if observed_entries != expected_entries:
        raise ArtifactIntegrityError(
            "personalized candidate manifest entries do not match the expected clients and rounds",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return manifest


def load_reused_personalized_candidates(
    request: ReusedPersonalizedCandidatesRequest,
) -> tuple[PersonalizedCandidateSet, ...]:
    manifest = validated_personalized_manifest(request)
    personalized_frame = read_parquet(
        request.global_history_directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    )
    training_rounds = tuple(
        RoundNumber(value) for value in range(1, request.checkpoint_protocol.maximum_round.value + 1)
    )
    validate_personalized_history(
        personalized_frame,
        expected_rounds=training_rounds,
        expected_clients=request.clients,
    )
    losses = tuple(
        ClientRoundLoss(
            client_id=str(client_id),
            round_number=RoundNumber(int(round_number)),
            loss=MetricValue(float(loss)),
        )
        for round_number, client_id, loss in personalized_frame.select(
            (
                FederatedHistoryColumn.ROUND_NUMBER.value,
                FederatedHistoryColumn.CLIENT_ID.value,
                FederatedHistoryColumn.LOCAL_LOSS.value,
            )
        ).iter_rows()
    )
    return tuple(
        PersonalizedCandidateSet(
            client=client,
            candidates=tuple(
                _personalized_candidate(request, client, entry, losses)
                for entry in manifest.entries
                if entry.client_id == client.client_id
            ),
        )
        for client in request.clients
    )


def _personalized_candidate(
    request: ReusedPersonalizedCandidatesRequest,
    client: ClientIdentity,
    entry: CandidateManifestEntry,
    losses: tuple[ClientRoundLoss, ...],
) -> CheckpointCandidate:
    path = request.personalized_output_directory / entry.tensor_name
    actual = checksum_file(path)
    if actual != entry.tensor_checksum:
        raise ArtifactIntegrityError(
            "reused personalized checkpoint checksum mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    matching = tuple(
        item.loss
        for item in losses
        if item.client_id == client.client_id and item.round_number == entry.round_number
    )
    if len(matching) != 1:
        raise ArtifactIntegrityError(
            "personalized checkpoint requires exactly one matching client-round loss",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return CheckpointCandidate(
        coordinate=request.personalized_coordinate,
        round_number=entry.round_number,
        client=client,
        tensor_path=path,
        tensor_checksum=actual,
        mean_training_loss=matching[0],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


def stage_personalized_candidates(
    *,
    coordinate: FederatedTrainingCoordinate,
    snapshot_sets: Sequence[PersonalizedSnapshotSet],
    checkpoint_protocol: CheckpointProtocol,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    output_directory: Path,
) -> tuple[tuple[PersonalizedCandidateSet, ...], Checksum]:
    candidate_sets = tuple(
        PersonalizedCandidateSet(
            client=snapshot_set.client,
            candidates=retain_checkpoint_candidates(
                coordinate,
                snapshot_set.snapshots,
                checkpoint_protocol=checkpoint_protocol,
                autoencoder=autoencoder,
                output_directory=output_directory,
                preprocessing_state_set_checksum=preprocessing_state_set_checksum,
                split_manifest_checksum=split_manifest_checksum,
                client=snapshot_set.client,
            ),
        )
        for snapshot_set in snapshot_sets
    )
    manifest = build_manifest(
        kind=CandidateManifestKind.PERSONALIZED,
        coordinate=coordinate,
        candidates=tuple(candidate for item in candidate_sets for candidate in item.candidates),
        checkpoint_protocol=checkpoint_protocol,
        autoencoder=autoencoder,
        batch_size=batch_size,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    write_manifest(output_directory, manifest)
    return candidate_sets, write_completion(output_directory, manifest, include_history=False)
