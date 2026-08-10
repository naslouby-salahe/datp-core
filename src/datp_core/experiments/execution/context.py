"""Federated execution-context preparation and typed client handoffs."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ClientIdentityToken,
    ContractSubject,
    DatasetId,
    ExperimentId,
    FeatureName,
    FeatureNameSequence,
)
from datp_core.core.numeric import ProximalCoefficient
from datp_core.data.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS
from datp_core.data.populations.contracts import ClientIdentity, ControlledPartitionCondition, FamilyAssignment
from datp_core.data.populations.publication import (
    ConstructDeclaredPopulationRequest,
    ConstructPublishedPopulationRequest,
    ConstructPublishedSplitRequest,
    construct_declared_population,
    construct_published_population,
    construct_published_split,
)
from datp_core.data.preprocessing.models import (
    ClientPreprocessingResult,
    FederatedPreprocessingOutcome,
    FederatedPreprocessingRequest,
    PublishedFederatedPreprocessingRequest,
)
from datp_core.data.preprocessing.service import preprocess_federated, preprocess_published_federated
from datp_core.data.registry import dataset_binding, population_capabilities
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.checkpoints.protocols import ANCHOR_DIAGNOSTIC_SNAPSHOT_PROTOCOL, DIAGNOSTIC_SNAPSHOT_PROTOCOL
from datp_core.detector.scoring.models import ClientScoringInput
from datp_core.detector.training.contracts import AutoencoderProtocol, FedAvgProtocol, FedProxProtocol
from datp_core.detector.training.models import (
    ClientTrainingInput,
    FederatedTrainingCoordinate,
)
from datp_core.detector.training.protocols import (
    ANCHOR_FEDAVG_TRAINING_PROTOCOL,
    ANCHOR_NBAIOT_AUTOENCODER,
    CICIOT2023_AUTOENCODER,
    EDGE_IIOTSET_NUMERIC_AUTOENCODER,
    NBAIOT_AUTOENCODER,
    resolve_single_model_federated_training_protocol,
)
from datp_core.experiments.common.coordinates import (
    BOUNDED_EVIDENCE_POPULATIONS,
    ExperimentCoordinate,
    ExternalTemporalExecutionIdentity,
)
from datp_core.experiments.execution.layout import (
    ExecutionArtifactDirectory,
    bounded_evidence_seed_directory,
    federated_training_directory,
)
from datp_core.runtime.configuration import DATA_ROOT

EDGE_FEATURE_NAMES = FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedExecutionContext:
    coordinate: FederatedTrainingCoordinate
    execution_identity: ExternalTemporalExecutionIdentity | None
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[FamilyAssignment, ...]
    preprocessing: FederatedPreprocessingOutcome
    training_directory: Path


def training_autoencoder(dataset: DatasetId) -> AutoencoderProtocol:
    match dataset:
        case DatasetId.NBAIOT:
            return NBAIOT_AUTOENCODER
        case DatasetId.EDGE_IIOTSET:
            return EDGE_IIOTSET_NUMERIC_AUTOENCODER
        case DatasetId.CICIOT2023:
            return CICIOT2023_AUTOENCODER


def training_autoencoder_for(coordinate: ExperimentCoordinate) -> AutoencoderProtocol:
    if coordinate.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return ANCHOR_NBAIOT_AUTOENCODER
    return training_autoencoder(coordinate.dataset)


def training_feature_names(dataset: DatasetId) -> FeatureNameSequence:
    if dataset is DatasetId.EDGE_IIOTSET:
        return EDGE_FEATURE_NAMES
    return FeatureNameSequence(tuple(FeatureName(name) for name in dataset_binding(dataset).schema.feature_columns))


def training_protocol_for(coordinate: ExperimentCoordinate) -> FedAvgProtocol | FedProxProtocol:
    if coordinate.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return ANCHOR_FEDAVG_TRAINING_PROTOCOL
    return resolve_single_model_federated_training_protocol(
        model=coordinate.training_model,
        coefficient=coordinate.model_coefficient,
    )


def diagnostic_snapshot_protocol_for(coordinate: ExperimentCoordinate) -> DiagnosticSnapshotProtocol:
    if coordinate.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return ANCHOR_DIAGNOSTIC_SNAPSHOT_PROTOCOL
    return DIAGNOSTIC_SNAPSHOT_PROTOCOL


def federated_model_coefficient(coordinate: ExperimentCoordinate) -> ProximalCoefficient | None:
    protocol = training_protocol_for(coordinate)
    return protocol.coefficient if isinstance(protocol, FedProxProtocol) else None


def execution_identity_for(coordinate: ExperimentCoordinate) -> ExternalTemporalExecutionIdentity | None:
    if coordinate.population not in BOUNDED_EVIDENCE_POPULATIONS:
        return None
    return ExternalTemporalExecutionIdentity(
        experiment=coordinate.experiment,
        population=coordinate.population,
        evidence_role=coordinate.evidence_role,
        temporal_state=coordinate.temporal_state,
    )


def execution_context_cache_key(coordinate: ExperimentCoordinate, output_root: Path) -> tuple[object, ...]:
    """Deterministic identity of the resolved federated execution context.

    The resolved context depends on the population, training coordinate, execution
    identity, and output root only; it never depends on the threshold method or
    metric. Coordinates sharing this key resolve to an identical context, so a
    campaign may resolve it once and reuse it across all of its coordinates.
    """
    return (
        coordinate.population,
        coordinate.dataset,
        coordinate.training_seed,
        coordinate.split_protocol,
        coordinate.preprocessing_protocol,
        coordinate.training_model,
        federated_model_coefficient(coordinate),
        coordinate.controlled_partition_kind,
        coordinate.dirichlet_concentration,
        execution_identity_for(coordinate),
        output_root,
    )


def resolve_execution_context(coordinate: ExperimentCoordinate, output_root: Path) -> FederatedExecutionContext:
    declared_dataset = population_capabilities(coordinate.population).dataset
    if coordinate.dataset is not declared_dataset:
        raise ScientificContractError(
            ErrorMessage(
                f"coordinate dataset {coordinate.dataset.name} does not match the population's "
                f"declared dataset {declared_dataset.name}"
            ),
            subject=ContractSubject.COORDINATE,
        )
    training_coordinate = FederatedTrainingCoordinate(
        population=coordinate.population,
        training_seed=coordinate.training_seed,
        split_protocol=coordinate.split_protocol,
        preprocessing_identity=coordinate.preprocessing_protocol,
        model=coordinate.training_model,
        model_coefficient=federated_model_coefficient(coordinate),
        controlled_partition_kind=coordinate.controlled_partition_kind,
        dirichlet_concentration=coordinate.dirichlet_concentration,
    )
    execution_identity = execution_identity_for(coordinate)
    if execution_identity is None:
        controlled_condition = _controlled_partition_condition(coordinate)
        population_result = construct_declared_population(
            ConstructDeclaredPopulationRequest(
                population=coordinate.population,
                dataset=coordinate.dataset,
                canonical_root=DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / coordinate.dataset.value,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                controlled_condition=controlled_condition,
            )
        )
        preprocessing = preprocess_federated(
            FederatedPreprocessingRequest(
                population=coordinate.population,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                preprocessing_identity=coordinate.preprocessing_protocol,
                data_root=DATA_ROOT,
                dirichlet_condition=controlled_condition,
                capture_timestamp_column=None,
            )
        )
        clients = population_result.construction.manifest.clients
        family_assignments = population_result.construction.manifest.family_by_client
        training_directory = federated_training_directory(training_coordinate, output_root)
    else:
        root = bounded_evidence_seed_directory(execution_identity, coordinate.training_seed, output_root)
        population_directory = root / ExecutionArtifactDirectory.POPULATION
        split_directory = root / ExecutionArtifactDirectory.SPLIT
        population_result = construct_published_population(
            ConstructPublishedPopulationRequest(
                canonical_root=DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / coordinate.dataset.value,
                population=coordinate.population,
                execution_identity=execution_identity,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                output_directory=population_directory,
                overwrite=False,
            )
        )
        construct_published_split(
            ConstructPublishedSplitRequest(
                population=coordinate.population,
                execution_identity=execution_identity,
                population_manifest=population_result.population_manifest,
                membership=population_result.membership,
                partition_seed=coordinate.training_seed,
                output_directory=split_directory,
                overwrite=False,
                matched_static_reference_manifest=population_result.matched_static_reference_manifest,
                matched_static_reference_membership=population_result.matched_static_reference_membership,
            )
        )
        preprocessing = preprocess_published_federated(
            PublishedFederatedPreprocessingRequest(
                execution_identity=execution_identity,
                population_directory=population_directory,
                split_directory=split_directory,
                preprocessing_identity=coordinate.preprocessing_protocol,
                data_root=DATA_ROOT,
            )
        )
        clients = population_result.population_manifest.clients
        family_assignments = population_result.population_manifest.family_by_client
        training_directory = root / ExecutionArtifactDirectory.TRAINING
    return FederatedExecutionContext(
        coordinate=training_coordinate,
        execution_identity=execution_identity,
        clients=clients,
        family_by_client=family_assignments,
        preprocessing=preprocessing,
        training_directory=training_directory,
    )


def client_training_inputs(
    publications: tuple[ClientPreprocessingResult, ...],
    clients: tuple[ClientIdentity, ...],
    feature_names: FeatureNameSequence,
) -> tuple[ClientTrainingInput, ...]:
    return tuple(
        ClientTrainingInput(
            client=client_with_id(clients, ClientIdentityToken(publication.client_identity.value)),
            training_features=pl.read_parquet(publication.paths.train),
            validation_features=pl.read_parquet(publication.paths.calibration),
            feature_names=feature_names,
            preprocessing_state=publication.fitted_state,
        )
        for publication in publications
    )


def client_scoring_inputs(
    publications: tuple[ClientPreprocessingResult, ...],
    clients: tuple[ClientIdentity, ...],
) -> tuple[ClientScoringInput, ...]:
    return tuple(
        ClientScoringInput(
            client=client_with_id(clients, ClientIdentityToken(publication.client_identity.value)),
            calibration_features=pl.read_parquet(publication.paths.calibration),
            evaluation_features=pl.read_parquet(publication.paths.evaluation),
            future_recalibration_features=(
                pl.read_parquet(publication.paths.future_recalibration)
                if publication.paths.future_recalibration is not None
                else None
            ),
        )
        for publication in publications
    )


def client_with_id(clients: tuple[ClientIdentity, ...], client_id: ClientIdentityToken) -> ClientIdentity:
    matches = tuple(candidate for candidate in clients if candidate.client_id == client_id)
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(f"population manifest must contain exactly one client {client_id.value}")
        )
    return matches[0]


def _controlled_partition_condition(coordinate: ExperimentCoordinate) -> ControlledPartitionCondition | None:
    if coordinate.controlled_partition_kind is None:
        return None
    return ControlledPartitionCondition(
        kind=coordinate.controlled_partition_kind,
        concentration=coordinate.dirichlet_concentration,
    )
