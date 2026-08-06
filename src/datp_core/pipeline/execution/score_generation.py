"""Federated score generation from selected checkpoints."""

from pathlib import Path

from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.identifiers import FeatureNameSequence
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.execution.checkpoints import select_execution_checkpoint
from datp_core.pipeline.execution.context import FederatedExecutionContext, client_scoring_inputs
from datp_core.pipeline.execution.layout import ExecutionArtifactDirectory
from datp_core.pipeline.scoring.federated import materialize_federated_scores, publish_federated_scores
from datp_core.pipeline.scoring.models import (
    ClientScoringInput,
    FederatedScoreArtifactManifest,
    GenerateFederatedScoresRequest,
    ScoreGenerationRequest,
)
from datp_core.protocols.training import BATCH_SIZE, AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device


def score_execution_context(
    context: FederatedExecutionContext,
    *,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
) -> FederatedScoreArtifactManifest:
    selected = select_execution_checkpoint(
        context,
        autoencoder=autoencoder,
        feature_names=feature_names,
    )
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
