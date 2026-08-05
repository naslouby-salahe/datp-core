"""Federated and centralized detector training publication."""

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

import polars as pl
import torch

from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import (
    CentralizedModelId,
    CheckpointStatus,
    ContractSubject,
    PublicationStatus,
    TrainingHistoryColumn,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    CudaDeviceName,
    FeatureCount,
    FeatureNameSequence,
    LearningRate,
    MetricValue,
    RoundNumber,
    RowCount,
    Seed,
    WeightDecay,
    checksum_file,
    checksum_text,
)
from datp_core.learning.centralized.training import (
    CentralizedArtifactName,
    CentralizedEpochLoss,
    CentralizedOptimizerSummary,
    CentralizedTrainingCoordinate,
    CentralizedTrainingRequest,
    CentralizedTrainingResult,
    declared_centralized_training_values,
    require_no_hidden_scientific_defaults,
    train_centralized_autoencoder,
    training_history_frame,
)
from datp_core.learning.federated.common import (
    DittoTrainingArtifacts,
    FederatedTrainingArtifacts,
    GlobalFederatedProtocol,
    ditto_training_is_reusable,
    federated_training_is_reusable,
    load_reused_ditto_artifacts,
    load_reused_federated_artifacts,
    rebase_ditto_training,
    rebase_federated_training,
    validate_federated_training_inputs,
    write_ditto_training,
    write_federated_training,
)
from datp_core.learning.federated.ditto import DittoTrainingRequest
from datp_core.learning.federated.models import CheckpointCandidate, FederatedTrainingResult
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.checkpoints.records import CentralizedCheckpointCandidate
from datp_core.pipeline.checkpoints.service import (
    candidate_tensor_name,
    retain_centralized_checkpoint_candidates,
)
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    FunctionalRelatedArtifactCodec,
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_artifact,
    publish_related_artifacts,
)
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
    CheckpointProtocol,
)
from datp_core.runtime.compute import resolve_cuda_device


class DittoPublicationMember(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorRequest:
    request: DittoTrainingRequest
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: ClientCollection[ClientIdentity, tuple[CheckpointCandidate, ...]]


@dataclass(slots=True, eq=False, kw_only=True)
class TrainCentralizedDetectorRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainCentralizedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum


@dataclass(slots=True, eq=False, kw_only=True)
class CentralizedTrainingPublicationRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    training_protocol: CentralizedTrainingProtocol
    learning_rate: LearningRate
    batch_size: BatchSize
    weight_decay: WeightDecay


@dataclass(frozen=True, slots=True)
class CentralizedTrainingArtifacts:
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]


def train_federated_detector(request: TrainFederatedDetectorRequest) -> TrainFederatedDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(training_request.clients, training_request.autoencoder.widths[0])
    publication = publish_artifact(
        ArtifactPublication(
            target=training_request.output_directory,
            request=training_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_training,
                validator=federated_training_is_reusable,
                loader=load_reused_federated_artifacts,
                rebaser=rebase_federated_training,
            ),
            overwrite=request.overwrite,
        )
    )
    artifacts: FederatedTrainingArtifacts = publication.value
    return TrainFederatedDetectorResult(
        stage=PipelineStage.TRAIN_DETECTOR,
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
    )


def train_ditto_detector(request: TrainDittoDetectorRequest) -> TrainDittoDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(training_request.clients, training_request.autoencoder.widths[0])
    publication = publish_related_artifacts(
        RelatedArtifactPublication(
            request=training_request,
            members=(
                RelatedPublicationMember(
                    identity=DittoPublicationMember.GLOBAL.value,
                    target=training_request.global_output_directory,
                ),
                RelatedPublicationMember(
                    identity=DittoPublicationMember.PERSONALIZED.value,
                    target=training_request.personalized_output_directory,
                ),
            ),
            codec=FunctionalRelatedArtifactCodec(
                writer=write_ditto_training,
                validator=ditto_training_is_reusable,
                loader=load_reused_ditto_artifacts,
                rebaser=rebase_ditto_training,
            ),
            overwrite=request.overwrite,
        )
    )
    artifacts: DittoTrainingArtifacts = publication.value
    return TrainDittoDetectorResult(
        stage=PipelineStage.TRAIN_DETECTOR,
        publication_status=publication.status,
        global_training=artifacts.global_training,
        global_candidates=artifacts.global_candidates,
        personalized_candidates=ClientCollection(
            tuple(ClientOwned(item.client, item.candidates) for item in artifacts.personalized_candidates)
        ),
    )


def train_centralized_detector(request: TrainCentralizedDetectorRequest) -> TrainCentralizedDetectorResult:
    require_no_hidden_scientific_defaults()
    training_protocol, _, learning_rate, batch_size, weight_decay = declared_centralized_training_values()
    publication_request = CentralizedTrainingPublicationRequest(
        coordinate=request.coordinate,
        training_features=request.training_features,
        feature_names=request.feature_names,
        preprocessing_state=request.preprocessing_state,
        split_manifest_checksum=request.split_manifest_checksum,
        output_directory=request.output_directory,
        training_seed=request.training_seed,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=training_protocol,
        learning_rate=learning_rate,
        batch_size=batch_size,
        weight_decay=weight_decay,
    )
    validate_centralized_training_request(publication_request)
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_training,
                validator=centralized_training_is_reusable,
                loader=load_reused_centralized_training,
                rebaser=rebase_centralized_training,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedArtifactName.COMPLETE,
        )
    )
    artifacts: CentralizedTrainingArtifacts = publication.value
    return TrainCentralizedDetectorResult(
        stage=PipelineStage.TRAIN_DETECTOR,
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
        complete_digest=publication.complete_digest,
    )


def validate_centralized_training_request(request: CentralizedTrainingPublicationRequest) -> None:
    if request.autoencoder.widths[0] != len(request.feature_names):
        raise ScientificContractError(
            "autoencoder input width must match the feature schema",
            subject=ContractSubject.AUTOENCODER,
        )
    if request.coordinate.model is not CentralizedModelId.CENTRALIZED_AUTOENCODER:
        raise ScientificContractError(
            "train stage requires CENTRALIZED_AUTOENCODER",
            subject=request.coordinate.model,
        )


def write_centralized_training(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> CentralizedTrainingArtifacts:
    execution = train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=request.coordinate,
            training_features=request.training_features,
            feature_names=request.feature_names,
            preprocessing_state=request.preprocessing_state,
            split_manifest_checksum=request.split_manifest_checksum,
            output_directory=directory,
            training_seed=request.training_seed,
            autoencoder=request.autoencoder,
            training_protocol=request.training_protocol,
            checkpoint_protocol=request.checkpoint_protocol,
            learning_rate=request.learning_rate,
            batch_size=request.batch_size,
            benign_label=PopulationOutcomeLabel.BENIGN,
        )
    )
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, request.autoencoder)
    training_history_frame(training).write_parquet(directory / CentralizedArtifactName.TRAINING_HISTORY)
    (directory / CentralizedArtifactName.COMPLETE).write_text(
        centralized_training_complete_digest(training).value,
        encoding="utf-8",
    )
    return CentralizedTrainingArtifacts(training, candidates)


def centralized_training_is_reusable(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> bool:
    complete = directory / CentralizedArtifactName.COMPLETE
    model = directory / CentralizedArtifactName.MODEL_TENSORS
    history = directory / CentralizedArtifactName.TRAINING_HISTORY
    if not (complete.is_file() and model.is_file() and history.is_file()):
        return False
    if any(
        not (directory / candidate_tensor_name(candidate)).is_file()
        for candidate in request.checkpoint_protocol.candidates
    ):
        return False
    try:
        expected = checksum_text(
            f"{checksum_file(model).value}|{request.checkpoint_protocol.maximum_round.value}|{request.batch_size.value}"
        )
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (OSError, ValueError):
        return False


def load_reused_centralized_training(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> CentralizedTrainingArtifacts:
    history = pl.read_parquet(directory / CentralizedArtifactName.TRAINING_HISTORY)
    epoch_losses = tuple(
        CentralizedEpochLoss(
            epoch=RoundNumber(int(epoch)),
            mean_training_loss=MetricValue(float(loss)),
        )
        for epoch, loss in history.select(
            (
                TrainingHistoryColumn.EPOCH.value,
                TrainingHistoryColumn.MEAN_TRAINING_LOSS.value,
            )
        ).iter_rows()
    )
    candidates = tuple(
        _load_reused_candidate(request, directory, candidate_round, epoch_losses)
        for candidate_round in request.checkpoint_protocol.candidates
    )
    model_path = directory / CentralizedArtifactName.MODEL_TENSORS
    training = CentralizedTrainingResult(
        coordinate=request.coordinate,
        autoencoder_widths=tuple(request.autoencoder.widths),
        optimizer=CentralizedOptimizerSummary(
            identity=request.training_protocol.optimizer.identity,
            learning_rate=request.learning_rate,
            weight_decay=request.weight_decay,
            batch_size=request.batch_size,
        ),
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=request.training_protocol,
        training_seed=request.training_seed,
        train_row_count=RowCount(request.training_features.height),
        feature_count=FeatureCount(len(request.feature_names)),
        epoch_losses=epoch_losses,
        model_directory=directory,
        model_tensor_path=model_path,
        model_tensor_checksum=checksum_file(model_path),
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=CudaDeviceName(torch.cuda.get_device_name(resolve_cuda_device())),
        batch_size_used=request.batch_size,
        final_epoch=request.checkpoint_protocol.maximum_round,
    )
    return CentralizedTrainingArtifacts(training, candidates)


def rebase_centralized_training(
    result: CentralizedTrainingArtifacts,
    directory: Path,
) -> CentralizedTrainingArtifacts:
    model_path = directory / CentralizedArtifactName.MODEL_TENSORS
    training = replace(
        result.training,
        model_directory=directory,
        model_tensor_path=model_path,
        model_tensor_checksum=checksum_file(model_path),
    )
    candidates = tuple(
        replace(
            candidate,
            tensor_path=directory / candidate_tensor_name(candidate.round_number),
            tensor_checksum=checksum_file(directory / candidate_tensor_name(candidate.round_number)),
        )
        for candidate in result.candidates
    )
    return CentralizedTrainingArtifacts(training, candidates)


def centralized_training_complete_digest(training: CentralizedTrainingResult) -> Checksum:
    return checksum_text(
        f"{training.model_tensor_checksum.value}|{training.final_epoch.value}|{training.batch_size_used.value}"
    )


def _load_reused_candidate(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
    candidate_round: RoundNumber,
    epoch_losses: tuple[CentralizedEpochLoss, ...],
) -> CentralizedCheckpointCandidate:
    path = directory / candidate_tensor_name(candidate_round)
    if not path.is_file():
        raise ArtifactIntegrityError(
            "reused checkpoint candidate missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    matching_losses = tuple(item.mean_training_loss for item in epoch_losses if item.epoch == candidate_round)
    if len(matching_losses) != 1:
        raise ArtifactIntegrityError(
            "reused checkpoint candidate requires exactly one matching training loss",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return CentralizedCheckpointCandidate(
        coordinate=request.coordinate,
        round_number=candidate_round,
        tensor_path=path,
        tensor_checksum=checksum_file(path),
        mean_training_loss=matching_losses[0],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        training_seed=request.training_seed,
        autoencoder_widths=tuple(request.autoencoder.widths),
    )
