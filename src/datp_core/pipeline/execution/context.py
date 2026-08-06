"""Federated execution-context preparation and typed client handoffs."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.datasets.registry import dataset_binding, population_capabilities
from datp_core.domain.enums import ContractSubject, DatasetId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.identifiers import FeatureName, FeatureNameSequence
from datp_core.domain.values.paths import FamilyIdentity
from datp_core.domain.values.ratios import ProximalCoefficient
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedTrainingCoordinate,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import preprocessing_state_set_checksum
from datp_core.pipeline.execution.layout import (
    ExecutionArtifactDirectory,
    bounded_evidence_seed_directory,
    federated_training_directory,
)
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.preparation.populations import (
    ConstructDeclaredPopulationRequest,
    ConstructPublishedPopulationRequest,
    ConstructPublishedSplitRequest,
    construct_declared_population,
    construct_published_population,
    construct_published_split,
)
from datp_core.pipeline.scoring.models import ClientScoringInput
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    FederatedPreprocessingOutcome,
    FederatedPreprocessingRequest,
    PublishedFederatedPreprocessingRequest,
)
from datp_core.preprocessing.service import preprocess_federated, preprocess_published_federated
from datp_core.protocols.experiments import BOUNDED_EVIDENCE_POPULATIONS, ExternalTemporalExecutionIdentity
from datp_core.protocols.training import (
    CICIOT2023_AUTOENCODER,
    EDGE_IIOTSET_NUMERIC_AUTOENCODER,
    NBAIOT_AUTOENCODER,
    AutoencoderProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    resolve_single_model_federated_training_protocol,
)
from datp_core.runtime.configuration import DATA_ROOT

EDGE_FEATURE_NAMES = FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedExecutionContext:
    coordinate: FederatedTrainingCoordinate
    execution_identity: ExternalTemporalExecutionIdentity | None
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]
    preprocessing: FederatedPreprocessingOutcome
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    training_directory: Path


def training_autoencoder(dataset: DatasetId) -> AutoencoderProtocol:
    match dataset:
        case DatasetId.NBAIOT:
            return NBAIOT_AUTOENCODER
        case DatasetId.EDGE_IIOTSET:
            return EDGE_IIOTSET_NUMERIC_AUTOENCODER
        case DatasetId.CICIOT2023:
            return CICIOT2023_AUTOENCODER


def training_feature_names(dataset: DatasetId) -> FeatureNameSequence:
    if dataset is DatasetId.EDGE_IIOTSET:
        return EDGE_FEATURE_NAMES
    return FeatureNameSequence(tuple(FeatureName(name) for name in dataset_binding(dataset).schema.feature_columns))


def training_protocol_for(coordinate: ExperimentCoordinate) -> FedAvgProtocol | FedProxProtocol:
    return resolve_single_model_federated_training_protocol(
        model=coordinate.training_model,
        coefficient=coordinate.model_coefficient,
    )


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


def resolve_execution_context(coordinate: ExperimentCoordinate, output_root: Path) -> FederatedExecutionContext:
    declared_dataset = population_capabilities(coordinate.population).dataset
    if coordinate.dataset is not declared_dataset:
        raise ScientificContractError(
            f"coordinate dataset {coordinate.dataset.name} does not match the population's "
            f"declared dataset {declared_dataset.name}",
            subject=ContractSubject.COORDINATE,
        )
    training_coordinate = FederatedTrainingCoordinate(
        population=coordinate.population,
        training_seed=coordinate.training_seed,
        split_protocol=coordinate.split_protocol,
        preprocessing_identity=coordinate.preprocessing_protocol,
        model=coordinate.training_model,
        model_coefficient=federated_model_coefficient(coordinate),
    )
    execution_identity = execution_identity_for(coordinate)
    if execution_identity is None:
        population_result = construct_declared_population(
            ConstructDeclaredPopulationRequest(
                population=coordinate.population,
                dataset=coordinate.dataset,
                canonical_root=DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / coordinate.dataset.value,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                controlled_condition=None,
            )
        )
        preprocessing = preprocess_federated(
            FederatedPreprocessingRequest(
                population=coordinate.population,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                preprocessing_identity=coordinate.preprocessing_protocol,
                data_root=DATA_ROOT,
                dirichlet_condition=None,
                capture_timestamp_column=None,
            )
        )
        clients = population_result.construction.manifest.clients
        family_pairs = population_result.construction.manifest.family_by_client
        split_checksum = population_result.split_manifest.assignment_checksum
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
        split_result = construct_published_split(
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
        family_pairs = population_result.population_manifest.family_by_client
        split_checksum = split_result.manifest.assignment_checksum
        training_directory = root / ExecutionArtifactDirectory.TRAINING
    state_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client_with_id(clients, publication.client_identity.value),
                preprocessing_checksum=publication.fitted_state.estimator_checksum,
            )
            for publication in preprocessing.client_publications
        )
    )
    return FederatedExecutionContext(
        coordinate=training_coordinate,
        execution_identity=execution_identity,
        clients=clients,
        family_by_client=family_identities(clients, family_pairs),
        preprocessing=preprocessing,
        preprocessing_state_set_checksum=state_checksum,
        split_manifest_checksum=split_checksum,
        training_directory=training_directory,
    )


def client_training_inputs(
    publications: tuple[ClientPreprocessingResult, ...],
    clients: tuple[ClientIdentity, ...],
    feature_names: FeatureNameSequence,
) -> tuple[ClientTrainingInput, ...]:
    return tuple(
        ClientTrainingInput(
            client=client_with_id(clients, publication.client_identity.value),
            training_features=pl.read_parquet(publication.paths.train),
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
            client=client_with_id(clients, publication.client_identity.value),
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


def family_identities(
    clients: tuple[ClientIdentity, ...],
    family_by_client: tuple[tuple[str, str], ...],
) -> tuple[tuple[ClientIdentity, FamilyIdentity], ...]:
    return tuple((client_with_id(clients, client_id), FamilyIdentity(family)) for client_id, family in family_by_client)


def client_with_id(clients: tuple[ClientIdentity, ...], client_id: str) -> ClientIdentity:
    matches = tuple(candidate for candidate in clients if candidate.client_id == client_id)
    if len(matches) != 1:
        raise ScientificContractError(f"population manifest must contain exactly one client {client_id}")
    return matches[0]
