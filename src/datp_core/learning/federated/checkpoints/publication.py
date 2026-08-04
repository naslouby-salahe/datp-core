"""Write federated checkpoint publications into caller-owned empty directories."""

from collections.abc import Sequence
from pathlib import Path

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.learning.federated.checkpoints.candidates import (
    build_manifest,
    retain_checkpoint_candidates,
    stage_personalized_candidates,
    write_completion,
    write_manifest,
)
from datp_core.learning.federated.checkpoints.history import persist_federated_training_history
from datp_core.learning.federated.checkpoints.identities import CandidateManifestKind
from datp_core.learning.federated.models import (
    DittoTrainingOutcome,
    FederatedTrainingCoordinate,
    FederatedTrainingExecution,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    PersonalizedSnapshotSet,
    RoundSnapshot,
)


def write_federated_training(
    execution: FederatedTrainingExecution,
    output_directory: Path,
) -> FederatedTrainingOutcome:
    """Write one global training publication to an empty directory."""
    require_empty_directory(output_directory)
    result = execution.training_result
    persist_federated_training_history(result.history, output_directory, device_name=result.device_name)
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
    return FederatedTrainingOutcome(training_result=result, candidates=candidates)


def write_ditto_training(
    *,
    global_result: FederatedTrainingResult,
    global_snapshots: Sequence[RoundSnapshot],
    personalized_coordinate: FederatedTrainingCoordinate,
    personalized_snapshot_sets: Sequence[PersonalizedSnapshotSet],
    global_output_directory: Path,
    personalized_output_directory: Path,
) -> DittoTrainingOutcome:
    """Write linked Ditto global and personalized publications to empty directories."""
    require_separate_directories(global_output_directory, personalized_output_directory)
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
    write_completion(global_output_directory, global_manifest, include_history=True)
    return DittoTrainingOutcome(
        global_training_result=global_result,
        global_candidates=global_candidates,
        personalized_candidates=personalized_candidates,
    )


def require_empty_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ArtifactIntegrityError(
            "checkpoint publication directory must be empty",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def require_separate_directories(global_directory: Path, personalized_directory: Path) -> None:
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
