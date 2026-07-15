from dataclasses import dataclass
from typing import Protocol

from datp_core.domain.artifacts.lineage import TemporalWindowIdentity
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.learning.checkpoints import CheckpointDescriptor
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    ScoreGenerationSpec,
    TemporalScoreArtifactSet,
    TestScoreArtifactSet,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateCalibrationScoresRequest:
    processed_splits: ProcessedSplitResult
    checkpoint: CheckpointDescriptor
    scoring: ScoreGenerationSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationScoreGenerationResult:
    scores: CalibrationScoreArtifactSet


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateTestScoresRequest:
    processed_splits: ProcessedSplitResult
    checkpoint: CheckpointDescriptor
    scoring: ScoreGenerationSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class TestScoreGenerationResult:
    scores: TestScoreArtifactSet


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateTemporalScoresRequest:
    processed_splits: ProcessedSplitResult
    checkpoint: CheckpointDescriptor
    scoring: ScoreGenerationSpec
    window_identity: TemporalWindowIdentity


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalScoreGenerationResult:
    scores: TemporalScoreArtifactSet


class ScoreGenerator(Protocol):
    def generate_calibration_scores(
        self,
        request: GenerateCalibrationScoresRequest,
    ) -> CalibrationScoreGenerationResult: ...

    def generate_test_scores(self, request: GenerateTestScoresRequest) -> TestScoreGenerationResult: ...

    def generate_temporal_scores(self, request: GenerateTemporalScoresRequest) -> TemporalScoreGenerationResult: ...
