"""Shared federated execution context and artifact derivation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl
from pydantic import ValidationError

from datp_core.datasets.catalogue import dataset_binding
from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS
from datp_core.domain.enums import DatasetId, MetricId, PartitionRole, ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    ClientCount,
    FamilyIdentity,
    FeatureName,
    FeatureNameSequence,
    MetricValue,
    ProximalCoefficient,
    Seed,
    checksum_file,
)
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.evaluation.population import FederatedEvaluationDocument
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedTrainingCoordinate,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import FederatedTrainingRequest, preprocessing_state_set_checksum
from datp_core.pipeline.construct_population import (
    ConstructDeclaredPopulationRequest,
    ConstructPublishedPopulationRequest,
    ConstructPublishedSplitRequest,
    construct_declared_population,
    construct_published_population,
    construct_published_split,
)
from datp_core.pipeline.fit_preprocessing import (
    FitFederatedPreprocessingRequest,
    FitFederatedPreprocessingResult,
    FitPublishedFederatedPreprocessingRequest,
    fit_federated_preprocessing,
    fit_published_federated_preprocessing,
)
from datp_core.pipeline.generate_scores import GenerateFederatedScoresRequest, generate_federated_scores
from datp_core.pipeline.planning import CoordinateIdentitySegment, ExperimentCoordinate
from datp_core.pipeline.scoring.service import ClientScoringInput, FederatedScoreArtifactManifest
from datp_core.pipeline.select_checkpoint import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.pipeline.train_detector import TrainFederatedDetectorRequest, train_federated_detector
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import ClientPreprocessingResult
from datp_core.protocols.experiments import BOUNDED_EVIDENCE_POPULATIONS, ExternalTemporalExecutionIdentity
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.protocols.models import AutoencoderProtocol, FedAvgProtocol, FedProxProtocol
from datp_core.protocols.runtime import DATA_ROOT
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    EDGE_IIOTSET_NUMERIC_AUTOENCODER,
    LEARNING_RATE,
    NBAIOT_AUTOENCODER,
    resolve_single_model_federated_training_protocol,
)
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores

EDGE_FEATURE_NAMES = FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))


class ExecutionArtifactDirectory(StrEnum):
    CANONICAL_DATA = "canonical"
    POPULATION = "population"
    SPLIT = "split"
    TRAINING = "training"
    SCORES = "scores"


class ExecutionRootDirectory(StrEnum):
    FEDERATED = "federated"
    BOUNDED_EVIDENCE = "bounded_evidence"


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedExecutionContext:
    coordinate: FederatedTrainingCoordinate
    execution_identity: ExternalTemporalExecutionIdentity | None
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]
    preprocessing: FitFederatedPreprocessingResult
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
            raise ScientificContractError(
                "no autoencoder architecture is declared for CICIOT2023",
                subject=dataset,
            )


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
                canonical_root=(
                    DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA.value / coordinate.dataset.value
                ),
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                controlled_condition=None,
            )
        )
        preprocessing = fit_federated_preprocessing(
            FitFederatedPreprocessingRequest(
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
        raw_family_by_client = population_result.construction.manifest.family_by_client
        split_manifest_checksum = population_result.split_manifest.assignment_checksum
        training_directory = federated_training_directory(training_coordinate, output_root)
    else:
        root = bounded_evidence_seed_directory(execution_identity, coordinate.training_seed, output_root)
        population_directory = root / ExecutionArtifactDirectory.POPULATION.value
        split_directory = root / ExecutionArtifactDirectory.SPLIT.value
        population_result = construct_published_population(
            ConstructPublishedPopulationRequest(
                canonical_root=(
                    DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA.value / coordinate.dataset.value
                ),
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
        preprocessing = fit_published_federated_preprocessing(
            FitPublishedFederatedPreprocessingRequest(
                execution_identity=execution_identity,
                population_directory=population_directory,
                split_directory=split_directory,
                preprocessing_identity=coordinate.preprocessing_protocol,
                data_root=DATA_ROOT,
            )
        )
        clients = population_result.population_manifest.clients
        raw_family_by_client = population_result.population_manifest.family_by_client
        split_manifest_checksum = split_result.manifest.assignment_checksum
        training_directory = root / ExecutionArtifactDirectory.TRAINING.value
    state_set_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client_with_id(clients, item.client_identity.value),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return FederatedExecutionContext(
        coordinate=training_coordinate,
        execution_identity=execution_identity,
        clients=clients,
        family_by_client=family_identities(clients, raw_family_by_client),
        preprocessing=preprocessing,
        preprocessing_state_set_checksum=state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
        training_directory=training_directory,
    )


def score_execution_context(
    context: FederatedExecutionContext,
    *,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
) -> FederatedScoreArtifactManifest:
    training_protocol = resolve_single_model_federated_training_protocol(
        model=context.coordinate.model,
        coefficient=context.coordinate.model_coefficient,
    )
    training = train_federated_detector(
        TrainFederatedDetectorRequest(
            request=FederatedTrainingRequest(
                coordinate=context.coordinate,
                clients=client_training_inputs(context.preprocessing.client_publications, context.clients, feature_names),
                population_client_count=ClientCount(len(context.clients)),
                autoencoder=autoencoder,
                training_protocol=training_protocol,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                training_seed=context.coordinate.training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=context.split_manifest_checksum,
                output_directory=context.training_directory,
            ),
            overwrite=False,
        )
    )
    selected = select_federated_primary_checkpoint(
        SelectFederatedCheckpointRequest(
            coordinate=context.coordinate,
            client=None,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
            split_manifest_checksum=context.split_manifest_checksum,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    ).decision.selected
    return generate_federated_scores(
        GenerateFederatedScoresRequest(
            checkpoint=selected,
            autoencoder=autoencoder,
            feature_names=feature_names,
            clients=client_scoring_inputs(context.preprocessing.client_publications, context.clients),
            batch_size=BATCH_SIZE,
            output_directory=context.training_directory / ExecutionArtifactDirectory.SCORES.value,
            preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
            split_manifest_checksum=context.split_manifest_checksum,
            overwrite=False,
        )
    ).result.manifest


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
    return tuple(
        (client_with_id(clients, client_id), FamilyIdentity(family)) for client_id, family in family_by_client
    )


def client_with_id(clients: tuple[ClientIdentity, ...], client_id: str) -> ClientIdentity:
    matches = tuple(candidate for candidate in clients if candidate.client_id == client_id)
    if len(matches) != 1:
        raise ScientificContractError(f"population manifest must contain exactly one client {client_id}")
    return matches[0]


def eligible_calibration_scores(
    score_manifest: FederatedScoreArtifactManifest,
    role: PartitionRole = PartitionRole.CALIBRATION,
) -> tuple[ClientBenignCalibrationScores, ...]:
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    if role is PartitionRole.CALIBRATION:
        score_set_checksum = invariant.calibration_score_set_checksum
    elif role is PartitionRole.FUTURE_RECALIBRATION:
        score_set_checksum = invariant.future_recalibration_score_set_checksum
    else:
        raise ScientificContractError(
            "threshold calibration scores require a calibration partition role",
            subject=role,
        )
    if score_set_checksum is None:
        raise ScientificContractError(
            "the requested calibration score set is unavailable",
            subject=role,
        )
    return tuple(
        ClientBenignCalibrationScores(
            record.scored_client,
            score_manifest.coordinate,
            tuple(
                float(value)
                for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
            ),
            checksum_file(record.path),
            score_set_checksum,
        )
        for record in sorted(score_manifest.records_for(role), key=lambda item: item.scored_client)
    )


def load_evaluation_document(path: Path) -> FederatedEvaluationDocument:
    try:
        return FederatedEvaluationDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ScientificContractError(f"completed evaluation document is unreadable or invalid: {path}") from error


def population_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(f"required metric is unavailable: {metric.value}")
    return result.value


def federated_training_directory(coordinate: FederatedTrainingCoordinate, output_root: Path) -> Path:
    coefficient = (
        str(coordinate.model_coefficient.value)
        if coordinate.model_coefficient is not None
        else CoordinateIdentitySegment.NO_MODEL_COEFFICIENT.value
    )
    return (
        output_root
        / ExecutionRootDirectory.FEDERATED.value
        / coordinate.population.value
        / str(coordinate.training_seed.value)
        / coordinate.split_protocol.value
        / coordinate.preprocessing_identity.value
        / coordinate.model.value
        / coefficient
    )


def bounded_evidence_seed_directory(
    execution_identity: ExternalTemporalExecutionIdentity,
    partition_seed: Seed,
    output_root: Path,
) -> Path:
    temporal = (
        execution_identity.temporal_state.value
        if execution_identity.temporal_state is not None
        else CoordinateIdentitySegment.NON_TEMPORAL.value
    )
    return (
        output_root
        / ExecutionRootDirectory.BOUNDED_EVIDENCE.value
        / execution_identity.experiment.value
        / execution_identity.population.value
        / execution_identity.evidence_role.value
        / str(partition_seed.value)
        / temporal
    )
