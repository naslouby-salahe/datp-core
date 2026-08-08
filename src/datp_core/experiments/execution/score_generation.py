"""Federated score generation from selected checkpoints."""

from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import FeatureNameSequence, SplitProtocolId
from datp_core.detector.scoring.federated import publish_federated_scores
from datp_core.detector.scoring.models import (
    ClientScoringInput,
    FederatedScoreArtifactManifest,
    GenerateFederatedScoresRequest,
)
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.models import CheckpointCandidate
from datp_core.protocols.training import BATCH_SIZE


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
