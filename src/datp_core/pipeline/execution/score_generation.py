"""Federated score generation from selected checkpoints."""

from pathlib import Path

from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.identifiers import FeatureNameSequence
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.scoring.federated import publish_federated_scores
from datp_core.pipeline.scoring.models import (
    ClientScoringInput,
    FederatedScoreArtifactManifest,
    GenerateFederatedScoresRequest,
)
from datp_core.protocols.training import BATCH_SIZE, AutoencoderProtocol


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
    return publish_federated_scores(
        GenerateFederatedScoresRequest(
            checkpoint=checkpoint,
            scored_split_protocol=scored_split_protocol,
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
