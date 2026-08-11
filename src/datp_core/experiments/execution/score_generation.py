from pathlib import Path

from datp_core.core.identifiers import FeatureNameSequence, SplitProtocolId
from datp_core.detector.scoring.federated import publish_federated_scores
from datp_core.detector.scoring.models import (
    ClientScoringInput,
    FederatedScoreArtifactManifest,
    GenerateFederatedScoresRequest,
)
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.models import FederatedTrainingResult


def score_terminal_model(
    *,
    training: FederatedTrainingResult,
    scored_split_protocol: SplitProtocolId,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
    clients: tuple[ClientScoringInput, ...],
    output_directory: Path,
) -> FederatedScoreArtifactManifest:
    return publish_federated_scores(
        GenerateFederatedScoresRequest(
            training=training,
            scored_split_protocol=scored_split_protocol,
            autoencoder=autoencoder,
            feature_names=feature_names,
            clients=clients,
            batch_size=training.batch_size_used,
            output_directory=output_directory,
            overwrite=False,
        )
    ).manifest
