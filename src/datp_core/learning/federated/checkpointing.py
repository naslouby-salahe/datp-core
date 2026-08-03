"""Federated checkpoint publication, selection, persistence, and trusted reuse."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from json import dumps
from os import replace as atomic_replace
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

import polars as pl
import torch
from polars.exceptions import PolarsError
from pydantic import ValidationError
from safetensors.torch import load_file, save_file

from datp_core.artifacts.serialization import serialize_json_model
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CheckpointSelectionRule,
    CheckpointStatus,
    CommunicationEstimationMethod,
    ContractSubject,
    PopulationIdentityKind,
    ProcessedDataBranch,
    TrainingModelId,
)
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    ByteCount,
    Checksum,
    MetricValue,
    RoundNumber,
    RowCount,
    checksum_file,
    checksum_text,
)
from datp_core.learning.autoencoder import (
    AutoencoderStateView,
    build_autoencoder_for_state,
)
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    CheckpointDecision,
    ClientTrainingResult,
    CommunicationRecord,
    DittoTrainingOutcome,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingExecution,
    FederatedTrainingHistory,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedCandidateSet,
    PersonalizedModelStateReference,
    PersonalizedSnapshotSet,
    RoundSnapshot,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol
from datp_core.protocols.training import (
    fixed_terminal_checkpoint_status,
    require_non_test_checkpoint_selection_inputs,
)

_CANDIDATE_PREFIX = "checkpoint_round_"
_CANDIDATE_SUFFIX = ".safetensors"
_PERSONALIZED_INFIX = "_client_"
_MANIFEST_SCHEMA_VERSION = 1


class FederatedHistoryAssetName(StrEnum):
    ROUND_SUMMARY = "round_summary.parquet"
    CLIENT_ROUNDS = "client_rounds.parquet"
    PERSONALIZED_ROUNDS = "personalized_rounds.parquet"
    DEVICE_NAME = "device_name.txt"
    CANDIDATE_MANIFEST = "candidate_manifest.json"
    COMPLETE = "COMPLETE"


class FederatedHistoryColumn(StrEnum):
    ROUND_NUMBER = "round_number"
    AGGREGATE_LOSS = "aggregate_loss"
    UPLOAD_BYTES = "upload_bytes"
    DOWNLOAD_BYTES = "download_bytes"
    GLOBAL_STATE_CHECKSUM = "global_state_checksum"
    CLIENT_ID = "client_id"
    SAMPLE_COUNT = "sample_count"
    LOCAL_LOSS = "local_loss"
    STATE_CHECKSUM = "state_checksum"


ROUND_SUMMARY_SCHEMA: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.AGGREGATE_LOSS.value: pl.Float64,
    FederatedHistoryColumn.UPLOAD_BYTES.value: pl.Int64,
    FederatedHistoryColumn.DOWNLOAD_BYTES.value: pl.Int64,
    FederatedHistoryColumn.GLOBAL_STATE_CHECKSUM.value: pl.String,
}

CLIENT_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.CLIENT_ID.value: pl.String,
    FederatedHistoryColumn.SAMPLE_COUNT.value: pl.Int64,
    FederatedHistoryColumn.LOCAL_LOSS.value: pl.Float64,
}

PERSONALIZED_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.CLIENT_ID.value: pl.String,
    FederatedHistoryColumn.LOCAL_LOSS.value: pl.Float64,
    FederatedHistoryColumn.STATE_CHECKSUM.value: pl.String,
}


class CandidateManifestKind(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


class CandidateManifestEntry(StrictModel):
    round_number: int
    client_id: str | None
    tensor_name: str
    tensor_checksum: str


class CandidateManifest(StrictModel):
    schema_version: int
    kind: CandidateManifestKind
    coordinate_population: str
    coordinate_training_seed: int
    coordinate_split_protocol: str
    coordinate_preprocessing_identity: str
    coordinate_model: str
    coordinate_model_coefficient: float | None
    preprocessing_state_set_checksum: str
    split_manifest_checksum: str
    checkpoint_rounds: tuple[int, ...]
    autoencoder_widths: tuple[int, ...]
    batch_size: int
    linked_personalized_digest: str | None
    entries: tuple[CandidateManifestEntry, ...]


@dataclass(frozen=True, slots=True)
class ReusedGlobalCandidatesRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class ReusedFederatedTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ReusedDittoTrainingRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    global_directory: Path
    personalized_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


def candidate_tensor_name(
    round_number: RoundNumber,
    client: ClientIdentity | None = None,
) -> str:
    base = f"{_CANDIDATE_PREFIX}{round_number.value}"
    if client is not None:
        base = f"{base}{_PERSONALIZED_INFIX}{client.client_id}"
    return f"{base}{_CANDIDATE_SUFFIX}"


def _read_parquet(path: Path) -> pl.DataFrame:
    if not path.is_file():
        raise ArtifactIntegrityError(
            f"required Parquet artifact is missing: {path.name}",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    try:
        return pl.read_parquet(path)
    except (OSError, PolarsError) as exc:
        raise ArtifactIntegrityError(
            f"Parquet artifact is unreadable or invalid: {path.name}",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from exc


def validate_parquet_schema(
    frame: pl.DataFrame,
    expected_schema: Mapping[str, type[pl.DataType]],
) -> None:
    expected_columns = tuple(expected_schema)
    if tuple(frame.columns) != expected_columns:
        raise ArtifactIntegrityError(
            "Parquet columns do not match the exact declared schema order",
            subject=ContractSubject.SCHEMA,
        )
    for column, dtype in expected_schema.items():
        if frame.schema[column] != dtype:
            raise ArtifactIntegrityError(
                f"Parquet column {column!r} has type {frame.schema[column]}, expected {dtype}",
                subject=ContractSubject.SCHEMA,
            )


def validate_round_summary(
    frame: pl.DataFrame,
    expected_rounds: tuple[RoundNumber, ...],
) -> None:
    validate_parquet_schema(frame, ROUND_SUMMARY_SCHEMA)
    observed = tuple(
        RoundNumber(value) for value in frame.get_column(FederatedHistoryColumn.ROUND_NUMBER.value).to_list()
    )
    if observed != expected_rounds:
        raise ArtifactIntegrityError(
            "round summary rows must equal the exact ordered training rounds",
            subject=ContractSubject.SCHEMA,
        )


def _validate_client_rows(
    frame: pl.DataFrame,
    schema: Mapping[str, type[pl.DataType]],
    *,
    expected_rounds: tuple[RoundNumber, ...],
    expected_clients: tuple[ClientIdentity, ...],
    table_name: str,
) -> None:
    validate_parquet_schema(frame, schema)
    if frame.height < 1:
        raise ArtifactIntegrityError(
            f"{table_name} must contain rows",
            subject=ContractSubject.SCHEMA,
        )

    round_column = FederatedHistoryColumn.ROUND_NUMBER.value
    client_column = FederatedHistoryColumn.CLIENT_ID.value
    observed_pairs = tuple(
        (RoundNumber(int(row[round_column])), str(row[client_column])) for row in frame.iter_rows(named=True)
    )
    expected_pairs = tuple(
        (round_number, client.client_id) for round_number in expected_rounds for client in expected_clients
    )
    if observed_pairs != expected_pairs:
        raise ArtifactIntegrityError(
            f"{table_name} must contain one ordered row for every declared round and client",
            subject=ContractSubject.SCHEMA,
        )


def validate_client_history(
    frame: pl.DataFrame,
    *,
    expected_rounds: tuple[RoundNumber, ...],
    expected_clients: tuple[ClientIdentity, ...],
) -> None:
    _validate_client_rows(
        frame,
        CLIENT_ROUNDS_SCHEMA,
        expected_rounds=expected_rounds,
        expected_clients=expected_clients,
        table_name="client history",
    )


def validate_personalized_history(
    frame: pl.DataFrame,
    *,
    expected_rounds: tuple[RoundNumber, ...],
    expected_clients: tuple[ClientIdentity, ...],
) -> None:
    _validate_client_rows(
        frame,
        PERSONALIZED_ROUNDS_SCHEMA,
        expected_rounds=expected_rounds,
        expected_clients=expected_clients,
        table_name="personalized history",
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.tmp")
    staging.write_text(text, encoding="utf-8")
    atomic_replace(staging, path)


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

    build_autoencoder_for_state(
        autoencoder,
        loaded,
        device=torch.device("cpu"),
    )


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
    if observed != tuple(checkpoint_protocol.candidates):
        raise ScientificContractError(
            "checkpoint snapshots must equal the exact ordered protocol candidates",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )

    candidates = tuple(
        CheckpointCandidate(
            coordinate=coordinate,
            round_number=snapshot.round_number,
            client=client,
            tensor_path=output_directory / candidate_tensor_name(snapshot.round_number, client),
            tensor_checksum=persist_checkpoint_tensor(
                snapshot.state_dict,
                output_directory / candidate_tensor_name(snapshot.round_number, client),
                autoencoder,
            ),
            mean_training_loss=snapshot.mean_training_loss,
            status=CheckpointStatus.CANDIDATE,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
        )
        for snapshot in snapshots
    )
    _validate_candidate_rounds_and_paths(candidates, checkpoint_protocol)
    return candidates


def _build_manifest(
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
    entries = tuple(
        CandidateManifestEntry(
            round_number=candidate.round_number.value,
            client_id=candidate.client.client_id if candidate.client is not None else None,
            tensor_name=candidate.tensor_path.name,
            tensor_checksum=candidate.tensor_checksum.value,
        )
        for candidate in candidates
    )
    return CandidateManifest(
        schema_version=_MANIFEST_SCHEMA_VERSION,
        kind=kind,
        coordinate_population=coordinate.population.value,
        coordinate_training_seed=coordinate.training_seed.value,
        coordinate_split_protocol=coordinate.split_protocol.value,
        coordinate_preprocessing_identity=coordinate.preprocessing_identity.value,
        coordinate_model=coordinate.model.value,
        coordinate_model_coefficient=(
            coordinate.model_coefficient.value if coordinate.model_coefficient is not None else None
        ),
        preprocessing_state_set_checksum=preprocessing_state_set_checksum.value,
        split_manifest_checksum=split_manifest_checksum.value,
        checkpoint_rounds=tuple(round_number.value for round_number in checkpoint_protocol.candidates),
        autoencoder_widths=tuple(autoencoder.widths),
        batch_size=batch_size.value,
        linked_personalized_digest=(
            linked_personalized_digest.value if linked_personalized_digest is not None else None
        ),
        entries=entries,
    )


def _load_manifest(directory: Path) -> CandidateManifest:
    path = directory / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value
    if not path.is_file():
        raise ArtifactIntegrityError(
            "candidate manifest is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    try:
        manifest = CandidateManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        raise ArtifactIntegrityError(
            "candidate manifest is unreadable or invalid",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from exc
    if manifest.schema_version != _MANIFEST_SCHEMA_VERSION:
        raise ArtifactIntegrityError(
            "candidate manifest schema version is unsupported",
            subject=ContractSubject.SCHEMA,
        )
    return manifest


def _expected_publication_files(
    manifest: CandidateManifest,
    *,
    include_history: bool,
) -> tuple[str, ...]:
    names = [
        FederatedHistoryAssetName.CANDIDATE_MANIFEST.value,
        *(entry.tensor_name for entry in manifest.entries),
    ]
    if include_history:
        names.extend(
            [
                FederatedHistoryAssetName.ROUND_SUMMARY.value,
                FederatedHistoryAssetName.CLIENT_ROUNDS.value,
                FederatedHistoryAssetName.DEVICE_NAME.value,
            ]
        )
        if manifest.coordinate_model == TrainingModelId.DITTO_GLOBAL_AUTOENCODER.value:
            names.append(FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value)
    return tuple(sorted(names))


def _publication_digest(
    directory: Path,
    expected_files: Sequence[str],
) -> Checksum:
    payload = dumps(
        [
            {
                "name": name,
                "checksum": checksum_file(directory / name).value,
            }
            for name in sorted(expected_files)
        ],
        sort_keys=True,
        separators=(",", ":"),
    )
    return checksum_text(payload)


def _write_completion(
    directory: Path,
    manifest: CandidateManifest,
    *,
    include_history: bool,
) -> Checksum:
    expected_files = _expected_publication_files(
        manifest,
        include_history=include_history,
    )
    digest = _publication_digest(directory, expected_files)
    _atomic_write_text(
        directory / FederatedHistoryAssetName.COMPLETE.value,
        digest.value,
    )
    return digest


def _verify_completion(
    directory: Path,
    manifest: CandidateManifest,
    *,
    include_history: bool,
) -> Checksum:
    expected_without_complete = _expected_publication_files(
        manifest,
        include_history=include_history,
    )
    expected_all = set(expected_without_complete) | {FederatedHistoryAssetName.COMPLETE.value}
    actual_files = {path.name for path in directory.iterdir() if path.is_file()}
    if actual_files != expected_all:
        raise ArtifactIntegrityError(
            "publication files do not match the exact declared artifact set",
            subject=ContractSubject.ARTIFACT_PATH,
        )

    complete = directory / FederatedHistoryAssetName.COMPLETE.value
    try:
        stored = Checksum(complete.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError, ValueError) as exc:
        raise ArtifactIntegrityError(
            "completion marker is unreadable or invalid",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from exc
    recomputed = _publication_digest(directory, expected_without_complete)
    if stored != recomputed:
        raise ArtifactIntegrityError(
            "completion marker does not match the current publication",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return recomputed


def _new_staging_directory(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))


def _replace_directory(staging: Path, target: Path) -> None:
    if target.exists():
        rmtree(target)
    atomic_replace(staging, target)


def _cleanup_staging(staging: Path) -> None:
    if staging.exists():
        rmtree(staging)


def persist_federated_training_history(
    history: FederatedTrainingHistory,
    directory: Path,
    *,
    device_name: str,
) -> None:
    normalized_device = device_name.strip()
    if not normalized_device:
        raise ScientificContractError(
            "training publication requires a non-empty CUDA device name",
            subject=ContractSubject.CUDA,
        )

    round_rows = [
        (
            item.round_number.value,
            item.aggregate_loss.value,
            item.communication.estimated_upload_bytes.value,
            item.communication.estimated_download_bytes.value,
            item.global_state_reference.state_checksum.value,
        )
        for item in history.rounds
    ]
    client_rows = [
        (
            item.round_number.value,
            result.client.client_id,
            result.sample_count.value,
            result.local_loss.value,
        )
        for item in history.rounds
        for result in item.client_results
    ]
    personalized_rows = [
        (
            item.round_number.value,
            reference.client.client_id,
            reference.local_loss.value,
            reference.state_checksum.value,
        )
        for item in history.rounds
        for reference in item.personalized_state_references
    ]

    directory.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        round_rows,
        schema=ROUND_SUMMARY_SCHEMA,
        orient="row",
    ).write_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY.value)
    pl.DataFrame(
        client_rows,
        schema=CLIENT_ROUNDS_SCHEMA,
        orient="row",
    ).write_parquet(directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value)
    if personalized_rows:
        pl.DataFrame(
            personalized_rows,
            schema=PERSONALIZED_ROUNDS_SCHEMA,
            orient="row",
        ).write_parquet(directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value)
    _atomic_write_text(
        directory / FederatedHistoryAssetName.DEVICE_NAME.value,
        normalized_device,
    )


def rebase_checkpoint_candidates(
    candidates: Sequence[CheckpointCandidate],
    directory: Path,
) -> tuple[CheckpointCandidate, ...]:
    rebased: list[CheckpointCandidate] = []
    for candidate in candidates:
        path = directory / candidate_tensor_name(
            candidate.round_number,
            candidate.client,
        )
        if not path.is_file():
            raise ArtifactIntegrityError(
                "rebased checkpoint file is missing",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        if checksum_file(path) != candidate.tensor_checksum:
            raise ArtifactIntegrityError(
                "rebased checkpoint checksum does not match the original candidate",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        rebased.append(replace(candidate, tensor_path=path))
    return tuple(rebased)


def publish_federated_training(
    execution: FederatedTrainingExecution,
    output_directory: Path,
) -> FederatedTrainingOutcome:
    result = execution.training_result
    staging = _new_staging_directory(output_directory)
    try:
        persist_federated_training_history(
            result.history,
            staging,
            device_name=result.device_name,
        )
        candidates = retain_checkpoint_candidates(
            result.coordinate,
            execution.snapshots,
            checkpoint_protocol=result.checkpoint_protocol,
            autoencoder=result.autoencoder,
            output_directory=staging,
            preprocessing_state_set_checksum=result.preprocessing_state_set_checksum,
            split_manifest_checksum=result.split_manifest_checksum,
            client=None,
        )
        manifest = _build_manifest(
            kind=CandidateManifestKind.GLOBAL,
            coordinate=result.coordinate,
            candidates=candidates,
            checkpoint_protocol=result.checkpoint_protocol,
            autoencoder=result.autoencoder,
            batch_size=result.batch_size_used,
            preprocessing_state_set_checksum=result.preprocessing_state_set_checksum,
            split_manifest_checksum=result.split_manifest_checksum,
        )
        serialize_json_model(
            manifest,
            staging / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value,
        )
        _write_completion(staging, manifest, include_history=True)
        _replace_directory(staging, output_directory)
    finally:
        _cleanup_staging(staging)

    return FederatedTrainingOutcome(
        training_result=result,
        candidates=rebase_checkpoint_candidates(candidates, output_directory),
    )


def _require_separate_directories(
    global_directory: Path,
    personalized_directory: Path,
) -> None:
    global_resolved = global_directory.resolve()
    personalized_resolved = personalized_directory.resolve()
    if (
        global_resolved == personalized_resolved
        or global_resolved in personalized_resolved.parents
        or personalized_resolved in global_resolved.parents
    ):
        raise ScientificContractError(
            "Ditto global and personalized output directories must be disjoint",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _stage_personalized_candidates(
    *,
    coordinate: FederatedTrainingCoordinate,
    snapshot_sets: Sequence[PersonalizedSnapshotSet],
    checkpoint_protocol: CheckpointProtocol,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    output_directory: Path,
) -> tuple[
    Path,
    tuple[PersonalizedCandidateSet, ...],
    Checksum,
]:
    staging = _new_staging_directory(output_directory)
    all_candidates: list[CheckpointCandidate] = []
    candidate_sets: list[PersonalizedCandidateSet] = []
    for snapshot_set in snapshot_sets:
        candidates = retain_checkpoint_candidates(
            coordinate,
            snapshot_set.snapshots,
            checkpoint_protocol=checkpoint_protocol,
            autoencoder=autoencoder,
            output_directory=staging,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
            client=snapshot_set.client,
        )
        candidate_sets.append(
            PersonalizedCandidateSet(
                client=snapshot_set.client,
                candidates=candidates,
            )
        )
        all_candidates.extend(candidates)

    manifest = _build_manifest(
        kind=CandidateManifestKind.PERSONALIZED,
        coordinate=coordinate,
        candidates=tuple(all_candidates),
        checkpoint_protocol=checkpoint_protocol,
        autoencoder=autoencoder,
        batch_size=batch_size,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    serialize_json_model(
        manifest,
        staging / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value,
    )
    digest = _write_completion(staging, manifest, include_history=False)
    return staging, tuple(candidate_sets), digest


def publish_ditto_training(
    *,
    global_result: FederatedTrainingResult,
    global_snapshots: Sequence[RoundSnapshot],
    personalized_coordinate: FederatedTrainingCoordinate,
    personalized_snapshot_sets: Sequence[PersonalizedSnapshotSet],
    global_output_directory: Path,
    personalized_output_directory: Path,
) -> DittoTrainingOutcome:
    _require_separate_directories(
        global_output_directory,
        personalized_output_directory,
    )
    personalized_staging: Path | None = None
    global_staging: Path | None = None
    try:
        (
            personalized_staging,
            staged_personalized_candidates,
            personalized_digest,
        ) = _stage_personalized_candidates(
            coordinate=personalized_coordinate,
            snapshot_sets=personalized_snapshot_sets,
            checkpoint_protocol=global_result.checkpoint_protocol,
            autoencoder=global_result.autoencoder,
            batch_size=global_result.batch_size_used,
            preprocessing_state_set_checksum=global_result.preprocessing_state_set_checksum,
            split_manifest_checksum=global_result.split_manifest_checksum,
            output_directory=personalized_output_directory,
        )

        global_staging = _new_staging_directory(global_output_directory)
        persist_federated_training_history(
            global_result.history,
            global_staging,
            device_name=global_result.device_name,
        )
        global_candidates = retain_checkpoint_candidates(
            global_result.coordinate,
            global_snapshots,
            checkpoint_protocol=global_result.checkpoint_protocol,
            autoencoder=global_result.autoencoder,
            output_directory=global_staging,
            preprocessing_state_set_checksum=global_result.preprocessing_state_set_checksum,
            split_manifest_checksum=global_result.split_manifest_checksum,
            client=None,
        )
        manifest = _build_manifest(
            kind=CandidateManifestKind.GLOBAL,
            coordinate=global_result.coordinate,
            candidates=global_candidates,
            checkpoint_protocol=global_result.checkpoint_protocol,
            autoencoder=global_result.autoencoder,
            batch_size=global_result.batch_size_used,
            preprocessing_state_set_checksum=global_result.preprocessing_state_set_checksum,
            split_manifest_checksum=global_result.split_manifest_checksum,
            linked_personalized_digest=personalized_digest,
        )
        serialize_json_model(
            manifest,
            global_staging / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value,
        )
        _write_completion(global_staging, manifest, include_history=True)

        _replace_directory(
            personalized_staging,
            personalized_output_directory,
        )
        _replace_directory(
            global_staging,
            global_output_directory,
        )
    finally:
        if personalized_staging is not None:
            _cleanup_staging(personalized_staging)
        if global_staging is not None:
            _cleanup_staging(global_staging)

    personalized_candidates = tuple(
        PersonalizedCandidateSet(
            client=item.client,
            candidates=rebase_checkpoint_candidates(
                item.candidates,
                personalized_output_directory,
            ),
        )
        for item in staged_personalized_candidates
    )
    return DittoTrainingOutcome(
        global_training_result=global_result,
        global_candidates=rebase_checkpoint_candidates(
            global_candidates,
            global_output_directory,
        ),
        personalized_candidates=personalized_candidates,
    )


def _validate_candidate_rounds_and_paths(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
) -> None:
    if tuple(candidate.round_number for candidate in candidates) != tuple(protocol.candidates):
        raise ArtifactIntegrityError(
            "checkpoint candidate rounds do not match the protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    paths = tuple(candidate.tensor_path for candidate in candidates)
    if len(set(paths)) != len(paths):
        raise ArtifactIntegrityError(
            "checkpoint candidate paths must be unique",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _verify_candidate_file(candidate: CheckpointCandidate) -> None:
    if candidate.tensor_path.suffix != _CANDIDATE_SUFFIX:
        raise ArtifactIntegrityError(
            "federated checkpoints must use SafeTensors",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if not candidate.tensor_path.is_file():
        raise ArtifactIntegrityError(
            "checkpoint candidate file is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if checksum_file(candidate.tensor_path) != candidate.tensor_checksum:
        raise ArtifactIntegrityError(
            "checkpoint candidate checksum mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
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
                "checkpoint candidate coordinate mismatch",
                subject=ContractSubject.COORDINATE,
            )
        if candidate.client != client:
            raise ScientificContractError(
                "checkpoint candidate client mismatch",
                subject=ContractSubject.CLIENT_IDENTITY,
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
        _verify_candidate_file(candidate)


def _statused_candidates(
    candidates: tuple[CheckpointCandidate, ...],
    maximum_round: RoundNumber,
) -> tuple[tuple[CheckpointCandidate, ...], CheckpointCandidate]:
    statused = tuple(
        replace(
            candidate,
            status=fixed_terminal_checkpoint_status(
                candidate.round_number,
                maximum_round,
            ),
        )
        for candidate in candidates
    )
    selected = tuple(
        candidate for candidate in statused if candidate.status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE
    )
    if len(selected) != 1:
        raise ArtifactIntegrityError(
            "fixed-terminal checkpoint selection did not produce exactly one selected candidate",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )
    return statused, selected[0]


def select_checkpoint(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    coordinate: FederatedTrainingCoordinate,
    client: ClientIdentity | None,
    selection_rule: CheckpointSelectionRule,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
) -> CheckpointDecision:
    require_non_test_checkpoint_selection_inputs(
        selection_rule=selection_rule,
        held_out_metrics=held_out_metrics,
        attack_labels_present=attack_labels_present,
        branch_label=ProcessedDataBranch.FEDERATED,
    )
    ordered = tuple(candidates)
    _validate_candidate_rounds_and_paths(ordered, protocol)
    validate_candidate_coordinates(
        ordered,
        coordinate,
        client=client,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    statused, selected = _statused_candidates(
        ordered,
        protocol.maximum_round,
    )
    return CheckpointDecision(
        coordinate=coordinate,
        client=client,
        selected=selected,
        candidates=statused,
        checkpoint_protocol=protocol,
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )


def reject_centralized_checkpoint(
    marker_identity: FederatedTrainingCoordinate,
) -> None:
    raise LeakageError(
        f"centralized checkpoint cannot enter federated selection ({marker_identity})",
        subject=ContractSubject.CHECKPOINT_CANDIDATES,
    )


def _validate_manifest(
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
    if (
        manifest.coordinate_population != coordinate.population.value
        or manifest.coordinate_training_seed != coordinate.training_seed.value
        or manifest.coordinate_split_protocol != coordinate.split_protocol.value
        or manifest.coordinate_preprocessing_identity != coordinate.preprocessing_identity.value
        or manifest.coordinate_model != coordinate.model.value
        or manifest.coordinate_model_coefficient
        != (coordinate.model_coefficient.value if coordinate.model_coefficient is not None else None)
    ):
        raise ArtifactIntegrityError(
            "candidate manifest coordinate does not match the requested experiment",
            subject=ContractSubject.COORDINATE,
        )
    if manifest.kind is not kind:
        raise ArtifactIntegrityError(
            "candidate manifest kind mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if manifest.preprocessing_state_set_checksum != preprocessing_state_set_checksum.value:
        raise ArtifactIntegrityError(
            "candidate manifest preprocessing checksum mismatch",
            subject=ContractSubject.PREPROCESSING,
        )
    if manifest.split_manifest_checksum != split_manifest_checksum.value:
        raise ArtifactIntegrityError(
            "candidate manifest split checksum mismatch",
            subject=ContractSubject.SPLIT,
        )
    if manifest.checkpoint_rounds != tuple(round_number.value for round_number in checkpoint_protocol.candidates):
        raise ArtifactIntegrityError(
            "candidate manifest rounds do not match the checkpoint protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    if manifest.autoencoder_widths != tuple(autoencoder.widths):
        raise ArtifactIntegrityError(
            "candidate manifest autoencoder architecture mismatch",
            subject=ContractSubject.WIDTHS,
        )
    if manifest.batch_size != batch_size.value:
        raise ArtifactIntegrityError(
            "candidate manifest batch size mismatch",
            subject=ContractSubject.BATCH_SIZE,
        )


def _validated_global_manifest(
    request: ReusedGlobalCandidatesRequest,
) -> CandidateManifest:
    manifest = _load_manifest(request.directory)
    _validate_manifest(
        manifest,
        kind=CandidateManifestKind.GLOBAL,
        coordinate=request.coordinate,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    _verify_completion(
        request.directory,
        manifest,
        include_history=True,
    )
    expected_entries = tuple(
        (
            round_number.value,
            None,
            candidate_tensor_name(round_number),
        )
        for round_number in request.checkpoint_protocol.candidates
    )
    observed_entries = tuple((entry.round_number, entry.client_id, entry.tensor_name) for entry in manifest.entries)
    if observed_entries != expected_entries:
        raise ArtifactIntegrityError(
            "global candidate manifest entries are incomplete, duplicated, or out of order",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return manifest


def _history_frames(directory: Path) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame | None]:
    round_frame = _read_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY.value)
    client_frame = _read_parquet(directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value)
    personalized_path = directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    personalized_frame = _read_parquet(personalized_path) if personalized_path.is_file() else None
    return round_frame, client_frame, personalized_frame


def load_reused_global_candidates(
    request: ReusedGlobalCandidatesRequest,
) -> tuple[CheckpointCandidate, ...]:
    manifest = _validated_global_manifest(request)
    round_frame, _, _ = _history_frames(request.directory)
    expected_training_rounds = tuple(
        RoundNumber(value) for value in range(1, request.checkpoint_protocol.maximum_round.value + 1)
    )
    validate_round_summary(round_frame, expected_training_rounds)
    loss_by_round = {
        RoundNumber(int(row[FederatedHistoryColumn.ROUND_NUMBER.value])): MetricValue(
            float(row[FederatedHistoryColumn.AGGREGATE_LOSS.value])
        )
        for row in round_frame.iter_rows(named=True)
    }

    candidates: list[CheckpointCandidate] = []
    for entry in manifest.entries:
        path = request.directory / entry.tensor_name
        actual = checksum_file(path)
        if actual.value != entry.tensor_checksum:
            raise ArtifactIntegrityError(
                "reused global checkpoint checksum mismatch",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        round_number = RoundNumber(entry.round_number)
        candidates.append(
            CheckpointCandidate(
                coordinate=request.coordinate,
                round_number=round_number,
                client=None,
                tensor_path=path,
                tensor_checksum=actual,
                mean_training_loss=loss_by_round[round_number],
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                split_manifest_checksum=request.split_manifest_checksum,
            )
        )
    return tuple(candidates)


def _validated_personalized_manifest(
    request: ReusedPersonalizedCandidatesRequest,
) -> CandidateManifest:
    manifest = _load_manifest(request.personalized_output_directory)
    _validate_manifest(
        manifest,
        kind=CandidateManifestKind.PERSONALIZED,
        coordinate=request.personalized_coordinate,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    _verify_completion(
        request.personalized_output_directory,
        manifest,
        include_history=False,
    )
    expected_entries = tuple(
        (
            round_number.value,
            client.client_id,
            candidate_tensor_name(round_number, client),
        )
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
    manifest = _validated_personalized_manifest(request)
    personalized_frame = _read_parquet(
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
    loss_by_key = {
        (
            str(row[FederatedHistoryColumn.CLIENT_ID.value]),
            RoundNumber(int(row[FederatedHistoryColumn.ROUND_NUMBER.value])),
        ): MetricValue(float(row[FederatedHistoryColumn.LOCAL_LOSS.value]))
        for row in personalized_frame.iter_rows(named=True)
    }
    entries_by_client = {
        client.client_id: tuple(entry for entry in manifest.entries if entry.client_id == client.client_id)
        for client in request.clients
    }

    result: list[PersonalizedCandidateSet] = []
    for client in request.clients:
        candidates: list[CheckpointCandidate] = []
        for entry in entries_by_client[client.client_id]:
            path = request.personalized_output_directory / entry.tensor_name
            actual = checksum_file(path)
            if actual.value != entry.tensor_checksum:
                raise ArtifactIntegrityError(
                    "reused personalized checkpoint checksum mismatch",
                    subject=ContractSubject.ARTIFACT_PATH,
                )
            round_number = RoundNumber(entry.round_number)
            candidates.append(
                CheckpointCandidate(
                    coordinate=request.personalized_coordinate,
                    round_number=round_number,
                    client=client,
                    tensor_path=path,
                    tensor_checksum=actual,
                    mean_training_loss=loss_by_key[(client.client_id, round_number)],
                    status=CheckpointStatus.CANDIDATE,
                    preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                    split_manifest_checksum=request.split_manifest_checksum,
                )
            )
        result.append(
            PersonalizedCandidateSet(
                client=client,
                candidates=tuple(candidates),
            )
        )
    return tuple(result)


def load_published_device_name(directory: Path) -> str:
    path = directory / FederatedHistoryAssetName.DEVICE_NAME.value
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ArtifactIntegrityError(
            "published CUDA device name is unreadable",
            subject=ContractSubject.CUDA,
        ) from exc
    if not value:
        raise ArtifactIntegrityError(
            "published CUDA device name is empty",
            subject=ContractSubject.CUDA,
        )
    return value


def load_federated_training_history(
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    identity_kind: PopulationIdentityKind,
    *,
    clients: tuple[ClientIdentity, ...],
    checkpoint_protocol: CheckpointProtocol,
    personalized_coordinate: FederatedTrainingCoordinate | None = None,
) -> FederatedTrainingHistory:
    round_frame, client_frame, personalized_frame = _history_frames(directory)
    training_rounds = tuple(RoundNumber(value) for value in range(1, checkpoint_protocol.maximum_round.value + 1))
    validate_round_summary(round_frame, training_rounds)
    validate_client_history(
        client_frame,
        expected_rounds=training_rounds,
        expected_clients=clients,
    )

    match coordinate.model:
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
            if personalized_coordinate is None or personalized_frame is None:
                raise ArtifactIntegrityError(
                    "Ditto global history requires its personalized coordinate and history",
                    subject=ContractSubject.COORDINATE,
                )
            if not coordinate.matches_ditto_peer(personalized_coordinate):
                raise ArtifactIntegrityError(
                    "Ditto global and personalized coordinates do not match",
                    subject=ContractSubject.COORDINATE,
                )
            validate_personalized_history(
                personalized_frame,
                expected_rounds=training_rounds,
                expected_clients=clients,
            )
        case TrainingModelId.FEDAVG_AUTOENCODER | TrainingModelId.FEDPROX_AUTOENCODER:
            if personalized_coordinate is not None or personalized_frame is not None:
                raise ArtifactIntegrityError(
                    "FedAvg and FedProx publications cannot contain personalized history",
                    subject=ContractSubject.ARTIFACT_PATH,
                )
        case _:
            raise ArtifactIntegrityError(
                "unsupported model in federated history publication",
                subject=ContractSubject.COORDINATE,
            )

    col = FederatedHistoryColumn
    client_rows_by_round = {
        round_number: client_frame.filter(pl.col(col.ROUND_NUMBER.value) == round_number.value)
        for round_number in training_rounds
    }
    personalized_rows_by_round = (
        {
            round_number: personalized_frame.filter(pl.col(col.ROUND_NUMBER.value) == round_number.value)
            for round_number in training_rounds
        }
        if personalized_frame is not None
        else {}
    )

    rounds: list[FederatedRoundResult] = []
    for row in round_frame.iter_rows(named=True):
        round_number = RoundNumber(int(row[col.ROUND_NUMBER.value]))
        client_results = tuple(
            ClientTrainingResult(
                client=ClientIdentity(
                    coordinate.population,
                    str(client_row[col.CLIENT_ID.value]),
                    identity_kind,
                ),
                sample_count=RowCount(int(client_row[col.SAMPLE_COUNT.value])),
                local_loss=MetricValue(float(client_row[col.LOCAL_LOSS.value])),
            )
            for client_row in client_rows_by_round[round_number].iter_rows(named=True)
        )
        personalized_references = (
            tuple(
                PersonalizedModelStateReference(
                    coordinate=personalized_coordinate,
                    client=ClientIdentity(
                        coordinate.population,
                        str(personalized_row[col.CLIENT_ID.value]),
                        identity_kind,
                    ),
                    round_number=round_number,
                    local_loss=MetricValue(float(personalized_row[col.LOCAL_LOSS.value])),
                    state_checksum=Checksum(str(personalized_row[col.STATE_CHECKSUM.value])),
                    tensor_path=None,
                )
                for personalized_row in personalized_rows_by_round[round_number].iter_rows(named=True)
            )
            if personalized_coordinate is not None
            else ()
        )
        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=client_results,
                aggregate_loss=MetricValue(float(row[col.AGGREGATE_LOSS.value])),
                communication=CommunicationRecord(
                    round_number=round_number,
                    estimated_upload_bytes=ByteCount(int(row[col.UPLOAD_BYTES.value])),
                    estimated_download_bytes=ByteCount(int(row[col.DOWNLOAD_BYTES.value])),
                    estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
                ),
                global_state_reference=GlobalModelStateReference(
                    coordinate=coordinate,
                    round_number=round_number,
                    state_checksum=Checksum(str(row[col.GLOBAL_STATE_CHECKSUM.value])),
                    tensor_path=None,
                ),
                personalized_state_references=personalized_references,
            )
        )
    return FederatedTrainingHistory(
        coordinate=coordinate,
        rounds=tuple(rounds),
    )


def load_reused_federated_training(
    request: ReusedFederatedTrainingRequest,
) -> FederatedTrainingOutcome:
    if request.coordinate.model not in {
        TrainingModelId.FEDAVG_AUTOENCODER,
        TrainingModelId.FEDPROX_AUTOENCODER,
    }:
        raise ArtifactIntegrityError(
            "Ditto reuse requires the typed Ditto reuse request",
            subject=ContractSubject.COORDINATE,
        )
    candidates = load_reused_global_candidates(
        ReusedGlobalCandidatesRequest(
            coordinate=request.coordinate,
            directory=request.directory,
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
        )
    )
    history = load_federated_training_history(
        request.coordinate,
        request.directory,
        request.identity_kind,
        clients=request.clients,
        checkpoint_protocol=request.checkpoint_protocol,
    )
    return FederatedTrainingOutcome(
        training_result=FederatedTrainingResult(
            coordinate=request.coordinate,
            autoencoder=request.autoencoder,
            checkpoint_protocol=request.checkpoint_protocol,
            history=history,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            device_name=load_published_device_name(request.directory),
            batch_size_used=request.batch_size,
        ),
        candidates=candidates,
    )


def load_reused_ditto_training(
    request: ReusedDittoTrainingRequest,
) -> DittoTrainingOutcome:
    global_request = ReusedGlobalCandidatesRequest(
        coordinate=request.global_coordinate,
        directory=request.global_directory,
        checkpoint_protocol=request.checkpoint_protocol,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
    )
    global_manifest = _validated_global_manifest(global_request)
    personalized_manifest = _validated_personalized_manifest(
        ReusedPersonalizedCandidatesRequest(
            personalized_coordinate=request.personalized_coordinate,
            personalized_output_directory=request.personalized_directory,
            global_history_directory=request.global_directory,
            clients=request.clients,
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
        )
    )
    personalized_digest = _verify_completion(
        request.personalized_directory,
        personalized_manifest,
        include_history=False,
    )
    if global_manifest.linked_personalized_digest != personalized_digest.value:
        raise ArtifactIntegrityError(
            "Ditto global publication is linked to a different personalized publication",
            subject=ContractSubject.ARTIFACT_PATH,
        )

    global_candidates = load_reused_global_candidates(global_request)
    personalized_candidates = load_reused_personalized_candidates(
        ReusedPersonalizedCandidatesRequest(
            personalized_coordinate=request.personalized_coordinate,
            personalized_output_directory=request.personalized_directory,
            global_history_directory=request.global_directory,
            clients=request.clients,
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
        )
    )
    history = load_federated_training_history(
        request.global_coordinate,
        request.global_directory,
        request.identity_kind,
        clients=request.clients,
        checkpoint_protocol=request.checkpoint_protocol,
        personalized_coordinate=request.personalized_coordinate,
    )
    result = FederatedTrainingResult(
        coordinate=request.global_coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=load_published_device_name(request.global_directory),
        batch_size_used=request.batch_size,
    )
    return DittoTrainingOutcome(
        global_training_result=result,
        global_candidates=global_candidates,
        personalized_candidates=personalized_candidates,
    )
