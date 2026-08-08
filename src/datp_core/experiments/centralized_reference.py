"""Privacy-incompatible centralized reference execution."""

from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.core.identifiers import (
    CentralizedModelId,
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.core.numeric import Seed
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.pipeline.checkpoints.service import (
    SelectCentralizedCheckpointRequest,
    select_centralized_primary_checkpoint,
)
from datp_core.pipeline.decision.centralized import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    ConstructCentralizedThresholdRequest,
    EvaluateCentralizedDetectorRequest,
    EvaluateCentralizedDetectorResult,
    construct_centralized_threshold,
    evaluate_centralized_detector,
)
from datp_core.pipeline.execution.context import training_feature_names
from datp_core.pipeline.execution.layout import ExecutionArtifactDirectory
from datp_core.pipeline.preparation.populations import ConstructDeclaredPopulationRequest, construct_declared_population
from datp_core.pipeline.scoring.centralized import generate_centralized_scores
from datp_core.pipeline.scoring.models import GenerateCentralizedScoresRequest
from datp_core.pipeline.training.centralized import TrainCentralizedDetectorRequest, train_centralized_detector
from datp_core.preprocessing.centralized import (
    CentralizedPopulationPreprocessingRequest,
    preprocess_centralized_population,
)
from datp_core.protocols.training import BATCH_SIZE, CHECKPOINT_PROTOCOL, NBAIOT_AUTOENCODER
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT


class CentralizedReferenceArtifactDirectory(StrEnum):
    ROOT = "centralized_reference"
    TRAINING = "training"
    SCORES = "scores"
    THRESHOLD = "threshold"
    EVALUATION = "evaluation"


def run_centralized_reference_seed(training_seed: Seed) -> EvaluateCentralizedDetectorResult:
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    population_result = construct_declared_population(
        ConstructDeclaredPopulationRequest(
            population=population,
            dataset=DatasetId.NBAIOT,
            canonical_root=DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / DatasetId.NBAIOT.value,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            controlled_condition=None,
        )
    )
    preprocessing = preprocess_centralized_population(
        CentralizedPopulationPreprocessingRequest(
            population=population,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    coordinate = CentralizedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )
    directory = centralized_reference_directory(training_seed)
    feature_names = training_feature_names(DatasetId.NBAIOT)
    split_checksum = population_result.split_manifest.assignment_checksum
    preprocessing_checksum = preprocessing.result.fitted_state.estimator_checksum
    training = train_centralized_detector(
        TrainCentralizedDetectorRequest(
            coordinate=coordinate,
            training_features=pl.read_parquet(preprocessing.result.paths.train),
            feature_names=feature_names,
            preprocessing_state=preprocessing.result.fitted_state,
            split_manifest_checksum=split_checksum,
            output_directory=directory / CentralizedReferenceArtifactDirectory.TRAINING,
            training_seed=training_seed,
            autoencoder=NBAIOT_AUTOENCODER,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            overwrite=False,
        )
    )
    selection = select_centralized_primary_checkpoint(
        SelectCentralizedCheckpointRequest(
            coordinate=coordinate,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            preprocessing_checksum=preprocessing_checksum,
            split_checksum=split_checksum,
            training_seed=training_seed,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    )
    scores = generate_centralized_scores(
        GenerateCentralizedScoresRequest(
            coordinate=coordinate,
            checkpoint=selection.selected,
            autoencoder=NBAIOT_AUTOENCODER,
            feature_names=feature_names,
            calibration_features=pl.read_parquet(preprocessing.result.paths.calibration),
            evaluation_features=pl.read_parquet(preprocessing.result.paths.evaluation),
            batch_size=BATCH_SIZE,
            output_directory=directory / CentralizedReferenceArtifactDirectory.SCORES,
            preprocessing_state_checksum=preprocessing_checksum,
            overwrite=False,
        )
    )
    threshold = construct_centralized_threshold(
        ConstructCentralizedThresholdRequest(
            coordinate=coordinate,
            calibration_scores=scores.scoring.calibration_scores,
            output_directory=directory / CentralizedReferenceArtifactDirectory.THRESHOLD,
            protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
            overwrite=False,
        )
    )
    return evaluate_centralized_detector(
        EvaluateCentralizedDetectorRequest(
            coordinate=coordinate,
            evaluation_scores=scores.scoring.evaluation_scores,
            threshold=threshold.threshold,
            output_directory=directory / CentralizedReferenceArtifactDirectory.EVALUATION,
            overwrite=False,
        )
    )


def centralized_reference_directory(training_seed: Seed) -> Path:
    return (
        OUTPUTS_ROOT
        / CentralizedReferenceArtifactDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / str(training_seed.value)
    )
