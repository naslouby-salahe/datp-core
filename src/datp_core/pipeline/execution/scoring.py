"""Checkpoint selection, scoring, matched references, and evaluation evidence loading."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from pydantic import ValidationError

from datp_core.datasets.edge_iiotset.schema import EdgeAssetRole
from datp_core.datasets.partitioning.contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    SplitManifestDocument,
)
from datp_core.domain.enums import ContractSubject, DatasetId, MetricId, PartitionRole, ScoreFrameColumn, SplitProtocolId, TemporalState
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, ClientCount, FeatureNameSequence, MetricValue, checksum_file
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.learning.federated.checkpoints.selection import CheckpointDecision
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.checkpoints.service import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.pipeline.execution.context import (
    FederatedExecutionContext,
    client_scoring_inputs,
    client_training_inputs,
    training_feature_names,
)
from datp_core.pipeline.execution.layout import ExecutionArtifactDirectory, bounded_evidence_seed_directory
from datp_core.pipeline.scoring.federated import materialize_federated_scores, publish_federated_scores
from datp_core.pipeline.scoring.models import (
    ClientScoringInput,
    FederatedScoreArtifactManifest,
    GenerateFederatedScoresRequest,
    ScoreGenerationRequest,
)
from datp_core.pipeline.training.federated import TrainFederatedDetectorRequest, train_federated_detector
from datp_core.preprocessing.models import ClientPreprocessingResult
from datp_core.preprocessing.service import (
    CANONICAL_DATA_DIRECTORY,
    MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET,
    MATCHED_STATIC_SPLIT_MANIFEST_ASSET,
    PARQUET_PATTERN,
)
from datp_core.preprocessing.state import TrustedScaler, load_estimator
from datp_core.preprocessing.validation import transform_feature_matrix
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.protocols.training import BATCH_SIZE, CHECKPOINT_PROTOCOL, LEARNING_RATE, resolve_single_model_federated_training_protocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.configuration import DATA_ROOT
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchedStaticReferenceInputs:
    clients: tuple[ClientScoringInput, ...]
    split_manifest_checksum: Checksum


def select_execution_checkpoint(
    context: FederatedExecutionContext,
    *,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
) -> CheckpointCandidate:
    protocol = resolve_single_model_federated_training_protocol(
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
                training_protocol=protocol,
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
    decision: CheckpointDecision = select_federated_primary_checkpoint(
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
    )
    return decision.selected


def score_execution_context(
    context: FederatedExecutionContext,
    *,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
) -> FederatedScoreArtifactManifest:
    selected = select_execution_checkpoint(context, autoencoder=autoencoder, feature_names=feature_names)
    return score_selected_checkpoint(
        checkpoint=selected,
        scored_split_protocol=context.coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=client_scoring_inputs(context.preprocessing.client_publications, context.clients),
        output_directory=context.training_directory / ExecutionArtifactDirectory.SCORES,
        preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
        split_manifest_checksum=context.split_manifest_checksum,
    )


def score_selected_checkpoint(
    *,
    checkpoint: CheckpointCandidate,
    scored_split_protocol: SplitProtocolId,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
    clients: tuple[ClientScoringInput, ...],
    output_directory: Path,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
) -> FederatedScoreArtifactManifest:
    if scored_split_protocol is checkpoint.coordinate.split_protocol:
        return publish_federated_scores(
            GenerateFederatedScoresRequest(
                checkpoint=checkpoint,
                autoencoder=autoencoder,
                feature_names=feature_names,
                clients=clients,
                batch_size=BATCH_SIZE,
                output_directory=output_directory,
                preprocessing_state_set_checksum=preprocessing_state_set_checksum,
                split_manifest_checksum=split_manifest_checksum,
                overwrite=False,
            )
        ).manifest
    return materialize_federated_scores(
        ScoreGenerationRequest(
            checkpoint=checkpoint,
            scored_split_protocol=scored_split_protocol,
            autoencoder=autoencoder,
            feature_names=feature_names,
            clients=clients,
            batch_size=BATCH_SIZE,
            output_directory=output_directory,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
        ),
        resolve_cuda_device(),
    ).manifest


def matched_static_reference_inputs(
    context: FederatedExecutionContext,
    output_root: Path,
) -> MatchedStaticReferenceInputs:
    identity = context.execution_identity
    if (
        identity is None
        or identity.population is not context.coordinate.population
        or identity.temporal_state not in (TemporalState.FROZEN_FUTURE, TemporalState.RECALIBRATED_FUTURE)
        or context.coordinate.split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    ):
        raise ScientificContractError(
            "matched static scoring requires a temporal historical execution context",
            subject=context.coordinate.population,
        )
    root = bounded_evidence_seed_directory(identity, context.coordinate.training_seed, output_root)
    split_directory = root / ExecutionArtifactDirectory.SPLIT
    try:
        split_manifest = SplitManifestDocument.model_validate_json(
            (split_directory / MATCHED_STATIC_SPLIT_MANIFEST_ASSET).read_text(encoding="utf-8")
        )
        assignments = pl.read_parquet(split_directory / MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET)
    except (OSError, ValueError, pl.exceptions.PolarsError) as error:
        raise ScientificContractError(
            "matched static split artifacts are missing or invalid",
            subject=context.coordinate.population,
        ) from error
    if split_manifest.split_protocol is not SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE:
        raise ScientificContractError(
            "matched static scoring requires the random-fractional static split",
            subject=split_manifest.split_protocol,
        )
    feature_names = training_feature_names(DatasetId.EDGE_IIOTSET)
    canonical_root = DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / DatasetId.EDGE_IIOTSET.value
    feature_scan = pl.scan_parquet(
        str(canonical_root / CANONICAL_DATA_DIRECTORY / EdgeAssetRole.TEMPORAL_BENIGN.value / PARQUET_PATTERN)
    ).select(
        (
            STABLE_ROW_ID_COLUMN,
            *(pl.col(name).cast(pl.Float64, strict=True).alias(name) for name in feature_names),
        )
    )
    joined = (
        assignments.lazy()
        .join(feature_scan, on=STABLE_ROW_ID_COLUMN, how="inner")
        .collect()
        .sort((CLIENT_ID_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN))
    )
    if joined.height != assignments.height:
        raise ScientificContractError(
            "matched static canonical feature join lost assignment rows",
            subject=context.coordinate.population,
        )
    observed_clients = frozenset(str(value) for value in joined.get_column(CLIENT_ID_COLUMN).unique().to_list())
    expected_clients = frozenset(client.client_id for client in context.clients)
    if observed_clients != expected_clients:
        raise ScientificContractError(
            "matched static and temporal client inventories must be identical",
            subject=context.coordinate.population,
        )
    return MatchedStaticReferenceInputs(
        clients=tuple(
            _matched_static_client_input(
                joined=joined,
                client=client,
                publication=_client_publication(context.preprocessing.client_publications, client),
                feature_names=feature_names,
            )
            for client in sorted(context.clients)
        ),
        split_manifest_checksum=split_manifest.assignment_checksum,
    )


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
        raise ScientificContractError("the requested calibration score set is unavailable", subject=role)
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


def _matched_static_client_input(
    *,
    joined: pl.DataFrame,
    client: ClientIdentity,
    publication: ClientPreprocessingResult,
    feature_names: FeatureNameSequence,
) -> ClientScoringInput:
    state = publication.fitted_state
    if state.protocol.input_feature_names != feature_names:
        raise ScientificContractError(
            "historical preprocessing schema does not match the static scoring schema",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    estimator = load_estimator(state.estimator_path, state.protocol.estimator_class_name)
    return ClientScoringInput(
        client=client,
        calibration_features=_transform_matched_static_partition(
            joined, client, PartitionRole.CALIBRATION, feature_names, estimator
        ),
        evaluation_features=_transform_matched_static_partition(
            joined, client, PartitionRole.EVALUATION, feature_names, estimator
        ),
    )


def _transform_matched_static_partition(
    joined: pl.DataFrame,
    client: ClientIdentity,
    role: PartitionRole,
    feature_names: FeatureNameSequence,
    estimator: TrustedScaler,
) -> pl.DataFrame:
    source = joined.filter(
        (pl.col(CLIENT_ID_COLUMN) == client.client_id) & (pl.col(PARTITION_ROLE_COLUMN).cast(pl.String) == role.value)
    ).select((STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names.names))
    if source.is_empty():
        raise ScientificContractError(
            f"matched static {role.value} partition is empty for {client.client_id}",
            subject=role,
        )
    transformed = transform_feature_matrix(
        estimator,
        source.select(feature_names.as_list()).to_numpy(),
        feature_names,
        role,
        description=f"matched static {role.value} matrix",
    )
    return source.select((STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN)).hstack(
        pl.from_numpy(transformed, schema=feature_names.as_list())
    )


def _client_publication(
    publications: tuple[ClientPreprocessingResult, ...],
    client: ClientIdentity,
) -> ClientPreprocessingResult:
    matches = tuple(item for item in publications if item.client_identity.value == client.client_id)
    if len(matches) != 1:
        raise ScientificContractError(
            f"expected one historical preprocessing state for {client.client_id}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]
