from dataclasses import dataclass

from datp_core.application.ports.learning import CentralizedTrainingRunResult
from datp_core.application.ports.scoring import (
    CalibrationScoreGenerationResult,
    CentralizedCalibrationScoreGenerationResult,
    CentralizedScoreGenerator,
    CentralizedTestScoreGenerationResult,
    GenerateCalibrationScoresRequest,
    GenerateCentralizedCalibrationScoresRequest,
    GenerateCentralizedTestScoresRequest,
    GenerateTemporalScoresRequest,
    GenerateTestScoresRequest,
    ScoreGenerator,
    TemporalScoreGenerationResult,
    TestScoreGenerationResult,
)
from datp_core.domain.artifacts.lineage import TemporalWindowIdentity
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.learning.checkpoints import CheckpointDescriptor
from datp_core.domain.learning.scores import B0ScoringBatchSpec, ScoreGenerationSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateTemporalScoresStageRequest:
    generator: ScoreGenerator
    processed_splits: ProcessedSplitResult
    checkpoint: CheckpointDescriptor
    scoring: ScoreGenerationSpec
    window_identity: TemporalWindowIdentity


def generate_calibration_scores(
    *,
    generator: ScoreGenerator,
    processed_splits: ProcessedSplitResult,
    checkpoint: CheckpointDescriptor,
    scoring: ScoreGenerationSpec,
) -> CalibrationScoreGenerationResult:
    return generator.generate_calibration_scores(
        GenerateCalibrationScoresRequest(processed_splits=processed_splits, checkpoint=checkpoint, scoring=scoring)
    )


def generate_test_scores(
    *,
    generator: ScoreGenerator,
    processed_splits: ProcessedSplitResult,
    checkpoint: CheckpointDescriptor,
    scoring: ScoreGenerationSpec,
) -> TestScoreGenerationResult:
    return generator.generate_test_scores(
        GenerateTestScoresRequest(processed_splits=processed_splits, checkpoint=checkpoint, scoring=scoring)
    )


def generate_temporal_scores(
    request: GenerateTemporalScoresStageRequest,
) -> TemporalScoreGenerationResult:
    return request.generator.generate_temporal_scores(
        GenerateTemporalScoresRequest(
            processed_splits=request.processed_splits,
            checkpoint=request.checkpoint,
            scoring=request.scoring,
            window_identity=request.window_identity,
        )
    )


def generate_centralized_calibration_scores(
    *,
    generator: CentralizedScoreGenerator,
    processed_splits: ProcessedSplitResult,
    checkpoint: CentralizedTrainingRunResult,
    scoring: B0ScoringBatchSpec,
) -> CentralizedCalibrationScoreGenerationResult:
    return generator.generate_calibration_scores(
        GenerateCentralizedCalibrationScoresRequest(
            processed_splits=processed_splits, checkpoint=checkpoint, scoring=scoring
        )
    )


def generate_centralized_test_scores(
    *,
    generator: CentralizedScoreGenerator,
    processed_splits: ProcessedSplitResult,
    checkpoint: CentralizedTrainingRunResult,
    scoring: B0ScoringBatchSpec,
) -> CentralizedTestScoreGenerationResult:
    return generator.generate_test_scores(
        GenerateCentralizedTestScoresRequest(processed_splits=processed_splits, checkpoint=checkpoint, scoring=scoring)
    )
