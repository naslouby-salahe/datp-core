from dataclasses import dataclass
from struct import pack

from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    SerializedPayloadEvidence,
    ThresholdBroadcastAccounting,
    ThresholdPayloadKind,
    ThresholdStageCommunicationDiagnostic,
)
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    CommunicationEstimationMethod,
    ContractSubject,
    FederatedThresholdMethod,
    MessageEndpoint,
)
from datp_core.core.numeric import ByteCount, ElapsedSeconds, LogicalElementCount, NonNegativeIntegerValue, RoundNumber
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.engine import serialize_model_state
from datp_core.detector.training.models import (
    DittoRuntimeEnvironment,
    FederatedTrainingCoordinate,
    FederatedTrainingResult,
    PersonalizedTerminalModel,
)


@dataclass(frozen=True, slots=True)
class DittoPersistentStateCost:
    client: ClientIdentity
    serialized_persistent_model_bytes: ByteCount
    extra_persistent_state_bytes_relative_to_fedavg: ByteCount

    def __post_init__(self) -> None:
        if self.serialized_persistent_model_bytes != self.extra_persistent_state_bytes_relative_to_fedavg:
            raise ScientificContractError(
                ErrorMessage("Ditto's extra persistent state must equal its per-client personalized model state"),
                subject=ContractSubject.RUNTIME,
            )


@dataclass(frozen=True, slots=True)
class DittoPersonalizedTrainingMeasurement:
    client: ClientIdentity
    round_number: RoundNumber
    wall_time: ElapsedSeconds


@dataclass(frozen=True, slots=True)
class DittoThresholdStageCost:
    method: FederatedThresholdMethod
    communication: ThresholdStageCommunicationDiagnostic

    def __post_init__(self) -> None:
        if self.method not in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }:
            raise ScientificContractError(
                ErrorMessage("Ditto cost accounting is defined for its locked shared/local threshold comparison"),
                subject=self.method,
            )


@dataclass(frozen=True, slots=True)
class DittoIncrementalStateAndCompute:
    """Measured host-relative Ditto cost evidence; deliberately not an IoT-device benchmark."""

    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    runtime_environment: DittoRuntimeEnvironment
    serialized_global_model_bytes: ByteCount
    persistent_state_by_client: tuple[DittoPersistentStateCost, ...]
    personalized_training_measurements: tuple[DittoPersonalizedTrainingMeasurement, ...]
    total_personalized_training_wall_time: ElapsedSeconds
    global_update_communication_bytes: ByteCount
    threshold_stage_costs: tuple[DittoThresholdStageCost, ...]

    def __post_init__(self) -> None:
        if not self.global_coordinate.matches_ditto_peer(self.personalized_coordinate):
            raise ScientificContractError(
                ErrorMessage("Ditto incremental costs require matching global and personalized coordinates"),
                subject=ContractSubject.COORDINATE,
            )
        if not self.persistent_state_by_client or not self.personalized_training_measurements:
            raise ScientificContractError(
                ErrorMessage("Ditto cost accounting requires persistent state and measured training")
            )
        state_clients = tuple(item.client for item in self.persistent_state_by_client)
        if len(state_clients) != len(set(state_clients)):
            raise ScientificContractError(ErrorMessage("Ditto persistent cost rows must be unique per client"))
        expected_total = sum(item.wall_time.value for item in self.personalized_training_measurements)
        if self.total_personalized_training_wall_time.value != expected_total:
            raise ScientificContractError(
                ErrorMessage("Ditto total personalized wall time must equal measured client-round times")
            )
        methods = tuple(item.method for item in self.threshold_stage_costs)
        if set(methods) != {FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD}:
            raise ScientificContractError(
                ErrorMessage("Ditto cost accounting requires shared and local threshold-stage linkage")
            )
        if len(methods) != len(set(methods)):
            raise ScientificContractError(ErrorMessage("Ditto threshold-stage costs must not repeat a method"))
        for item in self.threshold_stage_costs:
            if item.communication.coordinate != self.personalized_coordinate:
                raise ScientificContractError(
                    ErrorMessage("Ditto threshold-stage cost must use personalized-model scores")
                )


def shared_or_local_threshold_stage_communication(
    coordinate: FederatedTrainingCoordinate,
    method: FederatedThresholdMethod,
    clients: tuple[ClientIdentity, ...],
) -> ThresholdStageCommunicationDiagnostic:
    """Actual serializer-bound transport for the locked Ditto shared/local threshold comparison."""
    if method not in {FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD}:
        raise ScientificContractError(
            ErrorMessage("Ditto threshold-stage transport supports only shared/local methods")
        )
    ordered_clients = tuple(sorted(clients))
    if not ordered_clients:
        raise ScientificContractError(ErrorMessage("Ditto threshold-stage transport requires clients"))
    if method is FederatedThresholdMethod.LOCAL_THRESHOLD:
        messages: tuple[CommunicationMessageDiagnostic, ...] = ()
        rounds = NonNegativeIntegerValue(0)
    else:
        scalar = SerializedPayloadEvidence(ByteCount(len(pack("<d", 0.0))), LogicalElementCount(1))
        records: list[CommunicationMessageDiagnostic] = []
        for client in ordered_clients:
            records.extend(
                (
                    CommunicationMessageDiagnostic(
                        training_seed=coordinate.training_seed,
                        coordinate=coordinate,
                        sender=MessageEndpoint(f"client:{client.client_id.value}"),
                        receiver=MessageEndpoint("coordinator"),
                        direction=MessageDirection.CLIENT_TO_COORDINATOR,
                        payload_kind=ThresholdPayloadKind.LOCAL_QUANTILE_TRANSMISSION,
                        payload=scalar,
                        client=client,
                        group_identity=None,
                        estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
                    ),
                    CommunicationMessageDiagnostic(
                        training_seed=coordinate.training_seed,
                        coordinate=coordinate,
                        sender=MessageEndpoint("coordinator"),
                        receiver=MessageEndpoint(f"client:{client.client_id.value}"),
                        direction=MessageDirection.COORDINATOR_TO_CLIENT,
                        payload_kind=ThresholdPayloadKind.THRESHOLD_TRANSMISSION,
                        payload=scalar,
                        client=client,
                        group_identity=None,
                        estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
                    ),
                )
            )
        messages = tuple(records)
        rounds = NonNegativeIntegerValue(1)
    return ThresholdStageCommunicationDiagnostic(
        training_seed=coordinate.training_seed,
        coordinate=coordinate,
        messages=messages,
        total_logical_element_count=NonNegativeIntegerValue(
            sum(message.payload.logical_element_count.value for message in messages)
        ),
        total_serialized_bytes=ByteCount(sum(message.estimated_serialized_bytes.value for message in messages)),
        broadcast_accounting=ThresholdBroadcastAccounting.ONCE_PER_LOGICAL_RECIPIENT,
        communication_round_count=rounds,
    )


def ditto_incremental_state_and_compute(
    global_training: FederatedTrainingResult,
    personalized_terminal_models: tuple[PersonalizedTerminalModel, ...],
    runtime_environment: DittoRuntimeEnvironment,
    threshold_stage_costs: tuple[DittoThresholdStageCost, ...],
) -> DittoIncrementalStateAndCompute:
    rounds = global_training.history.rounds
    persistent_state_by_client = tuple(
        DittoPersistentStateCost(
            client=model.client,
            serialized_persistent_model_bytes=(serialized := serialize_model_state(model.model_state)).byte_count,
            extra_persistent_state_bytes_relative_to_fedavg=serialized.byte_count,
        )
        for model in personalized_terminal_models
    )
    measurements = tuple(
        DittoPersonalizedTrainingMeasurement(
            client=reference.client,
            round_number=reference.round_number,
            wall_time=reference.personalized_training_wall_time,
        )
        for round_result in rounds
        for reference in round_result.personalized_state_references
    )
    return DittoIncrementalStateAndCompute(
        global_coordinate=global_training.coordinate,
        personalized_coordinate=personalized_terminal_models[0].coordinate,
        runtime_environment=runtime_environment,
        serialized_global_model_bytes=rounds[0].communication.state_bytes,
        persistent_state_by_client=persistent_state_by_client,
        personalized_training_measurements=measurements,
        total_personalized_training_wall_time=ElapsedSeconds(sum(item.wall_time.value for item in measurements)),
        global_update_communication_bytes=ByteCount(
            sum(
                item.communication.estimated_upload_bytes.value + item.communication.estimated_download_bytes.value
                for item in rounds
            )
        ),
        threshold_stage_costs=threshold_stage_costs,
    )
