"""Stage: dispatch federated training across FedAvg, FedProx, and genuine Ditto."""

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, cast

from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum
from datp_core.learning.federated.checkpoints.candidates import rebase_checkpoint_candidates
from datp_core.learning.federated.checkpoints.identities import FederatedHistoryAssetName
from datp_core.learning.federated.checkpoints.reuse import (
    ReusedDittoTrainingRequest,
    ReusedFederatedTrainingRequest,
    load_reused_ditto_training,
    load_reused_federated_training,
)
from datp_core.learning.federated.ditto import DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import train_fedavg
from datp_core.learning.federated.fedprox import train_fedprox
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    ClientTrainingInput,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import FederatedTrainingRequest, preprocessing_state_set_checksum
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact
from datp_core.pipeline.publication.related import (
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_related_artifacts,
)
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import FedAvgProtocol, FedProxProtocol

type GlobalFederatedProtocol = FedAvgProtocol | FedProxProtocol


class DittoPublicationMember(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


@dataclass(frozen=True, slots=True)
class TrainFederatedRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainDittoRequest:
    request: DittoTrainingRequest
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFederatedStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_FEDERATED
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainDittoStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_FEDERATED
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: ClientCollection[ClientIdentity, tuple[CheckpointCandidate, ...]]


@dataclass(frozen=True, slots=True)
class _FederatedTrainingArtifacts:
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class _DittoTrainingArtifacts:
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: tuple[PersonalizedCandidateSet, ...]


@dataclass(frozen=True, slots=True)
class _FederatedTrainingCodec:
    def write(self, request: TrainFederatedRequest, directory: Path) -> _FederatedTrainingArtifacts:
        temporary_request = replace(request.request, output_directory=directory)
        match temporary_request.training_protocol:
            case FedAvgProtocol():
                outcome = train_fedavg(cast(FederatedTrainingRequest[FedAvgProtocol], temporary_request))
            case FedProxProtocol():
                outcome = train_fedprox(cast(FederatedTrainingRequest[FedProxProtocol], temporary_request))
        return _FederatedTrainingArtifacts(outcome.training_result, outcome.candidates)

    def validate(self, request: TrainFederatedRequest, directory: Path) -> bool:
        return _training_is_reusable(directory)

    def load(self, request: TrainFederatedRequest, directory: Path) -> _FederatedTrainingArtifacts:
        return _load_federated_artifacts(request.request, directory)

    def rebase(self, result: _FederatedTrainingArtifacts, directory: Path) -> _FederatedTrainingArtifacts:
        return _FederatedTrainingArtifacts(
            training=result.training,
            candidates=rebase_checkpoint_candidates(result.candidates, directory),
        )


@dataclass(frozen=True, slots=True)
class _DittoTrainingCodec:
    def write(self, request: TrainDittoRequest, directories: tuple[Path, ...]) -> _DittoTrainingArtifacts:
        global_directory, personalized_directory = _ditto_directories(directories)
        outcome = train_ditto(
            replace(
                request.request,
                global_output_directory=global_directory,
                personalized_output_directory=personalized_directory,
            )
        )
        return _DittoTrainingArtifacts(
            global_training=outcome.global_training_result,
            global_candidates=outcome.global_candidates,
            personalized_candidates=outcome.personalized_candidates,
        )

    def validate(self, request: TrainDittoRequest, directories: tuple[Path, ...]) -> bool:
        global_directory, personalized_directory = _ditto_directories(directories)
        return _training_is_reusable(global_directory) and _training_is_reusable(personalized_directory)

    def load(self, request: TrainDittoRequest, directories: tuple[Path, ...]) -> _DittoTrainingArtifacts:
        global_directory, personalized_directory = _ditto_directories(directories)
        return _load_ditto_artifacts(request.request, global_directory, personalized_directory)

    def rebase(self, result: _DittoTrainingArtifacts, directories: tuple[Path, ...]) -> _DittoTrainingArtifacts:
        global_directory, personalized_directory = _ditto_directories(directories)
        return _DittoTrainingArtifacts(
            global_training=result.global_training,
            global_candidates=rebase_checkpoint_candidates(result.global_candidates, global_directory),
            personalized_candidates=tuple(
                PersonalizedCandidateSet(
                    client=item.client,
                    candidates=rebase_checkpoint_candidates(item.candidates, personalized_directory),
                )
                for item in result.personalized_candidates
            ),
        )


def train_federated_stage(stage_request: TrainFederatedRequest) -> TrainFederatedStageResult:
    request = stage_request.request
    _validate_training_inputs(request.clients, request.autoencoder.widths[0])
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=stage_request,
            codec=_FederatedTrainingCodec(),
            overwrite=stage_request.overwrite,
            complete_marker=FederatedHistoryAssetName.COMPLETE.value,
        )
    )
    return TrainFederatedStageResult(
        publication_status=publication.status,
        training=publication.value.training,
        candidates=publication.value.candidates,
    )


def train_ditto_stage(stage_request: TrainDittoRequest) -> TrainDittoStageResult:
    request = stage_request.request
    _validate_training_inputs(request.clients, request.autoencoder.widths[0])
    publication = publish_related_artifacts(
        RelatedArtifactPublication(
            request=stage_request,
            members=(
                RelatedPublicationMember(
                    identity=DittoPublicationMember.GLOBAL.value,
                    target=request.global_output_directory,
                ),
                RelatedPublicationMember(
                    identity=DittoPublicationMember.PERSONALIZED.value,
                    target=request.personalized_output_directory,
                ),
            ),
            codec=_DittoTrainingCodec(),
            overwrite=stage_request.overwrite,
        )
    )
    artifacts = publication.value
    return TrainDittoStageResult(
        publication_status=publication.status,
        global_training=artifacts.global_training,
        global_candidates=artifacts.global_candidates,
        personalized_candidates=ClientCollection(
            tuple(ClientOwned(item.client, item.candidates) for item in artifacts.personalized_candidates)
        ),
    )


def _load_federated_artifacts(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
    directory: Path,
) -> _FederatedTrainingArtifacts:
    identity_kind = resolve_population(request.coordinate.population).declaration.identity_kind
    loaded = load_reused_federated_training(
        ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=directory,
            clients=tuple(client.client for client in request.clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=_compute_checksum(request.clients),
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    return _FederatedTrainingArtifacts(loaded.training_result, loaded.candidates)


def _load_ditto_artifacts(
    request: DittoTrainingRequest,
    global_directory: Path,
    personalized_directory: Path,
) -> _DittoTrainingArtifacts:
    identity_kind = resolve_population(request.global_coordinate.population).declaration.identity_kind
    loaded = load_reused_ditto_training(
        ReusedDittoTrainingRequest(
            global_coordinate=request.global_coordinate,
            personalized_coordinate=request.personalized_coordinate,
            global_directory=global_directory,
            personalized_directory=personalized_directory,
            clients=tuple(client.client for client in request.clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=_compute_checksum(request.clients),
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    return _DittoTrainingArtifacts(
        global_training=loaded.global_training_result,
        global_candidates=loaded.global_candidates,
        personalized_candidates=loaded.personalized_candidates,
    )


def _ditto_directories(directories: tuple[Path, ...]) -> tuple[Path, Path]:
    if len(directories) != 2:
        raise ValueError("Ditto publication requires global and personalized directories")
    return directories[0], directories[1]


def _training_is_reusable(directory: Path) -> bool:
    return (directory / FederatedHistoryAssetName.COMPLETE.value).is_file()


def _compute_checksum(clients: tuple[ClientTrainingInput, ...]) -> Checksum:
    return preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client.client,
                preprocessing_checksum=client.preprocessing_state.estimator_checksum,
            )
            for client in clients
        )
    )


def _validate_training_inputs(clients: tuple[ClientTrainingInput, ...], autoencoder_width: int) -> None:
    if not clients:
        raise ScientificContractError(
            "federated training requires client inputs",
            subject=ContractSubject.TRAINING,
        )
    feature_names = clients[0].feature_names
    if autoencoder_width != len(feature_names):
        raise ScientificContractError(
            "autoencoder input width must match the transformed feature schema",
            subject=ContractSubject.WIDTHS,
        )
    if any(client.feature_names != feature_names for client in clients):
        raise ScientificContractError(
            "federated clients must share one transformed feature schema",
            subject=ContractSubject.SCHEMA,
        )
