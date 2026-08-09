from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CommunicationEstimationMethod,
    ContractSubject,
    FeatureNameSequence,
    TrainingModelId,
)
from datp_core.core.numeric import ByteCount, LogicalElementCount, MetricValue, RoundNumber, RowCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.data.preprocessing.models import FederatedFittedPreprocessingState
from datp_core.detector.autoencoder import AutoencoderState
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


def validate_client_preprocessing_match(
    client: ClientIdentity,
    preprocessing_state: FederatedFittedPreprocessingState,
    feature_names: FeatureNameSequence,
) -> None:
    state_identity = preprocessing_state.client_identity
    if state_identity.value != client.client_id.value:
        raise ScientificContractError(
            ErrorMessage("preprocessing state client identity token must match the client training input"),
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if preprocessing_state.protocol.input_feature_names != feature_names:
        raise ScientificContractError(
            ErrorMessage("preprocessing transformed feature schema must match the declared training feature names"),
            subject=ContractSubject.SCHEMA,
        )


@dataclass(frozen=True, slots=True, eq=False)
class ClientTrainingInput:
    client: ClientIdentity
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: FederatedFittedPreprocessingState

    def __post_init__(self) -> None:
        if self.training_features.height < 1:
            raise ScientificContractError(
                ErrorMessage("client training input requires at least one benign training row"),
                subject=ContractSubject.ROWS,
            )
        validate_client_preprocessing_match(
            self.client,
            self.preprocessing_state,
            self.feature_names,
        )


@dataclass(frozen=True, slots=True)
class PreparedClientProvenance:
    client: ClientIdentity
    preprocessing_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ClientUpdate:
    client: ClientIdentity
    state_dict: AutoencoderState
    sample_count: RowCount
    local_loss: MetricValue

    def __post_init__(self) -> None:
        if self.sample_count.value < 1:
            raise ScientificContractError(
                ErrorMessage("a client update requires at least one training sample"),
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class ClientTrainingResult:
    client: ClientIdentity
    sample_count: RowCount
    local_loss: MetricValue

    @classmethod
    def from_update(cls, update: ClientUpdate) -> "ClientTrainingResult":
        return cls(
            client=update.client,
            sample_count=update.sample_count,
            local_loss=update.local_loss,
        )


@dataclass(frozen=True, slots=True)
class CommunicationRecord:
    round_number: RoundNumber
    estimated_upload_bytes: ByteCount
    estimated_download_bytes: ByteCount
    estimation_basis: CommunicationEstimationMethod
    state_bytes: ByteCount
    logical_element_count: LogicalElementCount

    def __post_init__(self) -> None:
        if self.estimation_basis is not CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE:
            raise ScientificContractError(
                ErrorMessage("communication bytes must remain tagged as serialized-message-size estimates"),
                subject=ContractSubject.RUNTIME,
            )


_GLOBAL_MODELS = frozenset(
    {
        TrainingModelId.FEDAVG_AUTOENCODER,
        TrainingModelId.FEDPROX_AUTOENCODER,
        TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
    }
)


@dataclass(frozen=True, slots=True)
class GlobalModelStateReference:
    coordinate: FederatedTrainingCoordinate
    round_number: RoundNumber
    state_checksum: Checksum
    tensor_path: Path | None

    def __post_init__(self) -> None:
        if self.coordinate.model not in _GLOBAL_MODELS:
            raise ScientificContractError(
                ErrorMessage("a global state reference requires a global federated model coordinate"),
                subject=ContractSubject.COORDINATE,
            )


@dataclass(frozen=True, slots=True)
class PersonalizedModelStateReference:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity
    round_number: RoundNumber
    local_loss: MetricValue
    state_checksum: Checksum
    tensor_path: Path | None

    def __post_init__(self) -> None:
        if self.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("personalized state references require the Ditto personalized coordinate"),
                subject=ContractSubject.COORDINATE,
            )
        if self.client.population != self.coordinate.population:
            raise ScientificContractError(
                ErrorMessage("personalized state client population must match its coordinate"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class FederatedRoundResult:
    round_number: RoundNumber
    client_results: tuple[ClientTrainingResult, ...]
    aggregate_loss: MetricValue
    communication: CommunicationRecord
    global_state_reference: GlobalModelStateReference
    personalized_state_references: tuple[PersonalizedModelStateReference, ...]

    def __post_init__(self) -> None:
        if not self.client_results:
            raise ScientificContractError(
                ErrorMessage("a federated round requires at least one client result"),
                subject=ContractSubject.CLIENT,
            )

        client_count = len(self.client_results)
        client_set = {result.client for result in self.client_results}

        if len(client_set) != client_count:
            raise ScientificContractError(
                ErrorMessage("a federated round cannot contain duplicate client results"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )

        if self.communication.round_number != self.round_number:
            raise ScientificContractError(
                ErrorMessage("communication round must match the training round"),
                subject=ContractSubject.COORDINATE,
            )
        if self.global_state_reference.round_number != self.round_number:
            raise ScientificContractError(
                ErrorMessage("global state round must match the training round"),
                subject=ContractSubject.COORDINATE,
            )

        coordinate = self.global_state_reference.coordinate
        personalized = self.personalized_state_references

        if personalized:
            personalized_count = len(personalized)
            personalized_client_set: set[ClientIdentity] = {reference.client for reference in personalized}

            if len(personalized_client_set) != personalized_count:
                raise ScientificContractError(
                    ErrorMessage("a federated round cannot contain duplicate personalized references"),
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
        else:
            personalized_client_set: set[ClientIdentity] = set()

        match coordinate.model:
            case TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
                if personalized_client_set != client_set:
                    raise ScientificContractError(
                        ErrorMessage("every Ditto global round requires exactly one personalized reference per client"),
                        subject=ContractSubject.CLIENT,
                    )
                for reference in personalized:
                    if reference.round_number != self.round_number:
                        raise ScientificContractError(
                            ErrorMessage("personalized state round must match the containing training round"),
                            subject=ContractSubject.COORDINATE,
                        )
                    if not coordinate.matches_ditto_peer(reference.coordinate):
                        raise ScientificContractError(
                            ErrorMessage("Ditto global and personalized references must share one experiment identity"),
                            subject=ContractSubject.COORDINATE,
                        )
            case TrainingModelId.FEDAVG_AUTOENCODER | TrainingModelId.FEDPROX_AUTOENCODER:
                if personalized:
                    raise ScientificContractError(
                        ErrorMessage("FedAvg and FedProx rounds cannot carry personalized references"),
                        subject=ContractSubject.COORDINATE,
                    )
            case _:
                raise ScientificContractError(
                    ErrorMessage("unsupported global model in a federated round"),
                    subject=ContractSubject.COORDINATE,
                )


@dataclass(frozen=True, slots=True)
class FederatedTrainingHistory:
    coordinate: FederatedTrainingCoordinate
    rounds: tuple[FederatedRoundResult, ...]

    def __post_init__(self) -> None:
        if not self.rounds:
            raise ScientificContractError(
                ErrorMessage("federated training history must contain at least one round"),
                subject=ContractSubject.TRAINING,
            )

        reference_clients = tuple(item.client for item in self.rounds[0].client_results)

        for expected_val, item in enumerate(self.rounds, start=1):
            if item.round_number.value != expected_val:
                raise ScientificContractError(
                    ErrorMessage("federated history rounds must be consecutive from one"),
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            if item.global_state_reference.coordinate != self.coordinate:
                raise ScientificContractError(
                    ErrorMessage("every training-history round must use the history coordinate"),
                    subject=ContractSubject.COORDINATE,
                )
            if tuple(result.client for result in item.client_results) != reference_clients:
                raise ScientificContractError(
                    ErrorMessage("every training-history round must preserve deterministic client ordering"),
                    subject=ContractSubject.CLIENT,
                )
