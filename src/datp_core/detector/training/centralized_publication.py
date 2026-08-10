from dataclasses import dataclass

import polars as pl

from datp_core.core.identifiers import FeatureNameSequence
from datp_core.core.numeric import Seed
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.data.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.training.centralized import (
    CentralizedTrainingCoordinate,
    CentralizedTrainingRequest,
    CentralizedTrainingResult,
    declared_centralized_training_values,
    require_no_hidden_scientific_defaults,
    train_centralized_autoencoder,
)
from datp_core.detector.training.contracts import AutoencoderProtocol


@dataclass(slots=True, eq=False, kw_only=True)
class TrainCentralizedDetectorRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainCentralizedDetectorResult:
    training: CentralizedTrainingResult


def train_centralized_detector(request: TrainCentralizedDetectorRequest) -> TrainCentralizedDetectorResult:
    require_no_hidden_scientific_defaults()
    defaults = declared_centralized_training_values()
    execution = train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=request.coordinate,
            training_features=request.training_features,
            feature_names=request.feature_names,
            preprocessing_state=request.preprocessing_state,
            training_seed=request.training_seed,
            autoencoder=request.autoencoder,
            training_protocol=defaults.training_protocol,
            diagnostic_snapshot_protocol=request.diagnostic_snapshot_protocol,
            learning_rate=defaults.learning_rate,
            batch_size=defaults.batch_size,
            benign_label=PopulationOutcomeLabel.BENIGN,
        )
    )
    return TrainCentralizedDetectorResult(training=execution.result)
