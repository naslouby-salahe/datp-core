from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_checksum, serialize_json_model
from datp_core.core.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.core.identifiers import ClientPathToken, ContractSubject, SafeTensorFilename, TrainingModelId
from datp_core.core.numeric import BatchSize, ManifestSchemaVersion, ModelCoefficientValue
from datp_core.detector.checkpoints.candidates import (
    retain_checkpoint_candidates,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.checkpoints.documents import (
    CandidateManifest,
    CandidateManifestEntry,
)
from datp_core.detector.checkpoints.history import (
    persist_federated_training_history,
)
from datp_core.detector.checkpoints.identities import (
    CandidateManifestKind,
    FederatedHistoryAssetName,
)
from datp_core.detector.training.models import (
    CheckpointCandidate,
    DittoTrainingOutcome,
    FederatedTrainingCoordinate,
    FederatedTrainingExecution,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
    PersonalizedSnapshotSet,
    RoundSnapshot,
)
from datp_core.protocols.training import AutoencoderProtocol

_MANIFEST_SCHEMA_VERSION = ManifestSchemaVersion(1)


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationFileChecksum:
    name: str
    checksum: Checksum


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
        autoencoder_widths=autoencoder.widths,
        batch_size=batch_size,
        linked_personalized_digest=linked_personalized_digest,
        entries=tuple(
            CandidateManifestEntry(
                round_number=candidate.round_number,
                client_id=(ClientPathToken(candidate.client.client_id) if candidate.client is not None else None),
                tensor_name=SafeTensorFilename(candidate.tensor_path.name),
                tensor_checksum=candidate.tensor_checksum,
            )
            for candidate in candidates
        ),
    )


def write_manifest(directory: Path, manifest: CandidateManifest) -> None:
    serialize_json_model(
        manifest,
        directory / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value,
    )


def load_manifest(directory: Path) -> CandidateManifest:
    path = directory / FederatedHistoryAssetName.CANDIDATE_MANIFEST.value
    if not path.is_file():
        raise ArtifactIntegrityError(
            "candidate manifest is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
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


def expected_publication_files(
    manifest: CandidateManifest,
    *,
    include_history: bool,
) -> tuple[str, ...]:
    names = [FederatedHistoryAssetName.CANDIDATE_MANIFEST.value]
    names.extend(entry.tensor_name for entry in manifest.entries)

    if not include_history:
        names.sort()
        return tuple(names)

    names.extend(
        (
            FederatedHistoryAssetName.ROUND_SUMMARY.value,
            FederatedHistoryAssetName.CLIENT_ROUNDS.value,
            FederatedHistoryAssetName.DEVICE_NAME.value,
        )
    )

    if manifest.coordinate_model is TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
        names.append(FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value)

    names.sort()
    return tuple(names)


def publication_digest(
    directory: Path,
    expected_files: Sequence[str],
) -> Checksum:
    projection = tuple(
        PublicationFileChecksum(
            name=name,
            checksum=checksum_file(directory / name),
        )
        for name in sorted(expected_files)
    )
    return canonical_checksum(projection)


def write_completion(
    directory: Path,
    manifest: CandidateManifest,
    *,
    include_history: bool,
) -> Checksum:
    digest = publication_digest(
        directory,
        expected_publication_files(
            manifest,
            include_history=include_history,
        ),
    )
    (directory / FederatedHistoryAssetName.COMPLETE.value).write_text(
        digest.value,
        encoding="utf-8",
    )
    return digest


def verify_completion(
    directory: Path,
    manifest: CandidateManifest,
    *,
    include_history: bool,
) -> Checksum:
    expected_without_complete = expected_publication_files(
        manifest,
        include_history=include_history,
    )
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
        ModelCoefficientValue(coordinate.model_coefficient.value) if coordinate.model_coefficient is not None else None
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

    if manifest.kind is not kind:
        raise ArtifactIntegrityError("candidate manifest kind mismatch", subject=ContractSubject.ARTIFACT_PATH)

    if manifest.preprocessing_state_set_checksum != preprocessing_state_set_checksum:
        raise ArtifactIntegrityError(
            "candidate manifest preprocessing checksum mismatch", subject=ContractSubject.PREPROCESSING
        )

    if manifest.split_manifest_checksum != split_manifest_checksum:
        raise ArtifactIntegrityError("candidate manifest split checksum mismatch", subject=ContractSubject.SPLIT)

    if manifest.checkpoint_rounds != checkpoint_protocol.candidates:
        raise ArtifactIntegrityError(
            "candidate manifest rounds do not match the checkpoint protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )

    if manifest.autoencoder_widths != autoencoder.widths:
        raise ArtifactIntegrityError(
            "candidate manifest autoencoder architecture mismatch", subject=ContractSubject.WIDTHS
        )

    if manifest.batch_size != batch_size:
        raise ArtifactIntegrityError("candidate manifest batch size mismatch", subject=ContractSubject.BATCH_SIZE)


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
        candidates=tuple(candidate for candidate_set in candidate_sets for candidate in candidate_set.candidates),
        checkpoint_protocol=checkpoint_protocol,
        autoencoder=autoencoder,
        batch_size=batch_size,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    write_manifest(output_directory, manifest)
    return candidate_sets, write_completion(
        output_directory,
        manifest,
        include_history=False,
    )


def write_federated_training(
    execution: FederatedTrainingExecution,
    output_directory: Path,
) -> FederatedTrainingOutcome:
    require_empty_directory(output_directory)
    result = execution.training_result
    persist_federated_training_history(
        result.history,
        output_directory,
        device_name=result.device_name,
    )
    candidates = retain_checkpoint_candidates(
        result.coordinate,
        execution.snapshots,
        checkpoint_protocol=result.checkpoint_protocol,
        autoencoder=result.autoencoder,
        output_directory=output_directory,
        preprocessing_state_set_checksum=result.preprocessing_state_set_checksum,
        split_manifest_checksum=result.split_manifest_checksum,
        client=None,
    )
    manifest = build_manifest(
        kind=CandidateManifestKind.GLOBAL,
        coordinate=result.coordinate,
        candidates=candidates,
        checkpoint_protocol=result.checkpoint_protocol,
        autoencoder=result.autoencoder,
        batch_size=result.batch_size_used,
        preprocessing_state_set_checksum=result.preprocessing_state_set_checksum,
        split_manifest_checksum=result.split_manifest_checksum,
    )
    write_manifest(output_directory, manifest)
    write_completion(output_directory, manifest, include_history=True)
    return FederatedTrainingOutcome(
        training_result=result,
        candidates=candidates,
    )


def write_ditto_training(
    *,
    global_result: FederatedTrainingResult,
    global_snapshots: Sequence[RoundSnapshot],
    personalized_coordinate: FederatedTrainingCoordinate,
    personalized_snapshot_sets: Sequence[PersonalizedSnapshotSet],
    global_output_directory: Path,
    personalized_output_directory: Path,
) -> DittoTrainingOutcome:
    require_separate_directories(
        global_output_directory,
        personalized_output_directory,
    )
    require_empty_directory(global_output_directory)
    require_empty_directory(personalized_output_directory)
    personalized_candidates, personalized_digest = stage_personalized_candidates(
        coordinate=personalized_coordinate,
        snapshot_sets=personalized_snapshot_sets,
        checkpoint_protocol=global_result.checkpoint_protocol,
        autoencoder=global_result.autoencoder,
        batch_size=global_result.batch_size_used,
        preprocessing_state_set_checksum=global_result.preprocessing_state_set_checksum,
        split_manifest_checksum=global_result.split_manifest_checksum,
        output_directory=personalized_output_directory,
    )
    persist_federated_training_history(
        global_result.history,
        global_output_directory,
        device_name=global_result.device_name,
    )
    global_candidates = retain_checkpoint_candidates(
        global_result.coordinate,
        global_snapshots,
        checkpoint_protocol=global_result.checkpoint_protocol,
        autoencoder=global_result.autoencoder,
        output_directory=global_output_directory,
        preprocessing_state_set_checksum=global_result.preprocessing_state_set_checksum,
        split_manifest_checksum=global_result.split_manifest_checksum,
        client=None,
    )
    global_manifest = build_manifest(
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
    write_manifest(global_output_directory, global_manifest)
    write_completion(
        global_output_directory,
        global_manifest,
        include_history=True,
    )
    return DittoTrainingOutcome(
        global_training_result=global_result,
        global_candidates=global_candidates,
        personalized_candidates=personalized_candidates,
    )


def require_empty_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if next(directory.iterdir(), None) is not None:
        raise ArtifactIntegrityError(
            "checkpoint publication directory must be empty",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def require_separate_directories(
    global_directory: Path,
    personalized_directory: Path,
) -> None:
    global_resolved = global_directory.resolve()
    personalized_resolved = personalized_directory.resolve()
    if (
        global_resolved == personalized_resolved
        or global_resolved.is_relative_to(personalized_resolved)
        or personalized_resolved.is_relative_to(global_resolved)
    ):
        raise ScientificContractError(
            "Ditto global and personalized output directories must be disjoint",
            subject=ContractSubject.ARTIFACT_PATH,
        )
