"""Stage: dispatch federated training across FedAvg, FedProx, and genuine Ditto."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientCount,
    FeatureNameSequence,
    LearningRate,
    RoundNumber,
    Seed,
)
from datp_core.learning.federated.checkpointing import (
    CheckpointCandidate,
    ReusedFederatedTrainingRequest,
    ReusedPersonalizedCandidatesRequest,
    candidate_set_digest,
    federated_training_directory_is_reusable,
    load_reused_federated_training,
    load_reused_personalized_candidates,
    rebase_checkpoint_candidates,
)
from datp_core.learning.federated.ditto import DittoTrainingOutcome, DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import train_fedavg
from datp_core.learning.federated.fedprox import train_fedprox
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedHistoryAssetName,
    FederatedTrainingCoordinate,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
)
from datp_core.learning.federated.training import (
    FederatedTrainingRequest,
    persist_federated_training_history,
    preprocessing_state_set_checksum,
)
from datp_core.orchestration.stages import _Box
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import ClientPreprocessPublication
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CheckpointProtocol,
    DittoProtocol,
    FedAvgProtocol,
    FedProxProtocol,
)


def _training_is_reusable(directory: Path, candidate_rounds: tuple[RoundNumber, ...]) -> bool:
    complete = directory / FederatedHistoryAssetName.COMPLETE.value
    if not complete.is_file():
        return False
    try:
        expected_digest = Checksum(complete.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError, ValueError):
        return False
    return federated_training_directory_is_reusable(directory, candidate_rounds, expected_digest)


@dataclass(frozen=True, slots=True)
class TrainFedAvgRequest:
    coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedAvgProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFedProxRequest:
    coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedProxProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainDittoRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: DittoProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    global_output_directory: Path
    personalized_output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFederatedStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainDittoStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates_by_client: dict[ClientIdentity, tuple[CheckpointCandidate, ...]]


def train_fedavg_stage(request: TrainFedAvgRequest) -> TrainFederatedStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_inputs(request.coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple((client.client, client.preprocessing_state.estimator_checksum) for client in clients)
    )
    box: _Box[FederatedTrainingOutcome] = _Box()

    def write(temporary: Path) -> None:
        outcome = train_fedavg(
            FederatedTrainingRequest(
                coordinate=request.coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=temporary,
            )
        )
        _publish_training_artifacts(temporary, outcome.training_result, outcome.candidates)
        box.value = outcome

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _training_is_reusable(directory, request.checkpoint_protocol.candidates),
            write=write,
            remove_target=rmtree,
        )
    )
    return _finalize_global_training_stage(
        reload=ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=request.output_directory,
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=resolve_population(request.coordinate.population).declaration.identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        ),
        outcome=box.value,
        reused=reused,
    )


def train_fedprox_stage(request: TrainFedProxRequest) -> TrainFederatedStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_inputs(request.coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple((client.client, client.preprocessing_state.estimator_checksum) for client in clients)
    )
    box: _Box[FederatedTrainingOutcome] = _Box()

    def write(temporary: Path) -> None:
        outcome = train_fedprox(
            FederatedTrainingRequest(
                coordinate=request.coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=temporary,
            )
        )
        _publish_training_artifacts(temporary, outcome.training_result, outcome.candidates)
        box.value = outcome

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _training_is_reusable(directory, request.checkpoint_protocol.candidates),
            write=write,
            remove_target=rmtree,
        )
    )
    return _finalize_global_training_stage(
        reload=ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=request.output_directory,
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=resolve_population(request.coordinate.population).declaration.identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        ),
        outcome=box.value,
        reused=reused,
    )


def train_ditto_stage(request: TrainDittoRequest) -> TrainDittoStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_inputs(request.global_coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple((client.client, client.preprocessing_state.estimator_checksum) for client in clients)
    )
    box: _Box[DittoTrainingOutcome] = _Box()

    def write_global(temporary: Path) -> None:
        if box.value is None:
            box.value = train_ditto(
                DittoTrainingRequest(
                    global_coordinate=request.global_coordinate,
                    personalized_coordinate=request.personalized_coordinate,
                    clients=clients,
                    population_client_count=request.population_client_count,
                    autoencoder=request.autoencoder,
                    training_protocol=request.training_protocol,
                    checkpoint_protocol=request.checkpoint_protocol,
                    training_seed=request.training_seed,
                    batch_size=request.batch_size,
                    learning_rate=request.learning_rate,
                    split_manifest_checksum=request.split_manifest_checksum,
                    global_output_directory=temporary,
                    personalized_output_directory=request.personalized_output_directory,
                )
            )
        _publish_training_artifacts(
            temporary,
            box.value.global_training_result,
            box.value.global_candidates,
        )

    reused = publish_atomically(
        AtomicPublication(
            target=request.global_output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _training_is_reusable(directory, request.checkpoint_protocol.candidates),
            write=write_global,
            remove_target=rmtree,
        )
    )
    if reused:
        return _finalize_reused_ditto_stage(request, clients, preprocessing_checksum)
    if box.value is None:
        raise ArtifactIntegrityError(
            "Ditto training write did not populate an outcome", subject=ContractSubject.TRAINING
        )
    global_candidates = rebase_checkpoint_candidates(
        box.value.global_candidates, request.global_output_directory, client=None
    )
    personalized_candidates = {
        pcs.client: rebase_checkpoint_candidates(
            pcs.candidates,
            request.personalized_output_directory,
            client=pcs.client,
        )
        for pcs in box.value.personalized_candidates
    }
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=PublicationStatus.PUBLISHED,
        global_training=box.value.global_training_result,
        global_candidates=global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _finalize_reused_ditto_stage(
    request: TrainDittoRequest,
    clients: tuple[ClientTrainingInput, ...],
    preprocessing_checksum: Checksum,
) -> TrainDittoStageResult:
    identity_kind = resolve_population(request.global_coordinate.population).declaration.identity_kind
    global_training, global_candidates = load_reused_federated_training(
        ReusedFederatedTrainingRequest(
            coordinate=request.global_coordinate,
            directory=request.global_output_directory,
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    reused_personalized_sets = load_reused_personalized_candidates(
        ReusedPersonalizedCandidatesRequest(
            personalized_coordinate=request.personalized_coordinate,
            personalized_output_directory=request.personalized_output_directory,
            global_history_directory=request.global_output_directory,
            clients=tuple(client.client for client in clients),
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    personalized_candidates = {pcs.client: pcs.candidates for pcs in reused_personalized_sets}
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=PublicationStatus.REUSED,
        global_training=global_training,
        global_candidates=global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _publish_training_artifacts(
    directory: Path,
    training_result: FederatedTrainingResult,
    candidates: tuple[CheckpointCandidate, ...],
) -> None:
    persist_federated_training_history(
        training_result.history,
        directory,
        device_name=training_result.device_name,
    )
    digest = candidate_set_digest(candidates)
    (directory / FederatedHistoryAssetName.COMPLETE.value).write_text(digest.value, encoding="utf-8")


def _finalize_global_training_stage(
    *,
    reload: ReusedFederatedTrainingRequest,
    outcome: FederatedTrainingOutcome | None,
    reused: bool,
) -> TrainFederatedStageResult:
    if reused:
        training, candidates = load_reused_federated_training(reload)
        status = PublicationStatus.REUSED
    else:
        if outcome is None:
            raise ArtifactIntegrityError(
                "federated training write did not populate an outcome", subject=ContractSubject.TRAINING
            )
        training = outcome.training_result
        candidates = rebase_checkpoint_candidates(outcome.candidates, reload.directory, client=None)
        status = PublicationStatus.PUBLISHED
    return TrainFederatedStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=status,
        training=training,
        candidates=candidates,
    )


def _client_inputs(
    coordinate: FederatedTrainingCoordinate,
    client_publications: tuple[ClientPreprocessPublication, ...],
) -> tuple[ClientTrainingInput, ...]:
    identity_kind = resolve_population(coordinate.population).declaration.identity_kind
    inputs: list[ClientTrainingInput] = []
    for publication in client_publications:
        client = ClientIdentity(coordinate.population, publication.client_identity.value, identity_kind)
        frame = pl.read_parquet(publication.result.train_path)
        training_input = ClientTrainingInput(
            client=client,
            training_features=frame,
            feature_names=FeatureNameSequence(publication.result.transformed_schema.feature_names),
            preprocessing_state=publication.result.fitted_state,
        )
        inputs.append(training_input)
    return tuple(inputs)


def _require_autoencoder_matches_preprocessing(
    autoencoder: AutoencoderProtocol,
    client_publications: tuple[ClientPreprocessPublication, ...],
) -> None:
    """Fail before training when a declared model cannot reconstruct its published feature space."""
    if not client_publications:
        raise ScientificContractError(
            "federated training requires published client preprocessing", subject=ContractSubject.TRAINING
        )
    expected_names = client_publications[0].result.transformed_schema.feature_names
    expected_width = len(expected_names)
    if autoencoder.widths[0] != expected_width or autoencoder.widths[-1] != expected_width:
        raise ScientificContractError(
            "autoencoder input and reconstruction widths must match the published transformed schema",
            subject=ContractSubject.WIDTHS,
        )
    if any(
        publication.result.transformed_schema.feature_names != expected_names for publication in client_publications
    ):
        raise ScientificContractError(
            "federated clients must publish one identical transformed feature schema",
            subject=ContractSubject.SCHEMA,
        )
