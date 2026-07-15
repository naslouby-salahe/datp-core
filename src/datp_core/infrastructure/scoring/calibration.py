from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import torch
from torch import Tensor, nn

from datp_core.application.ports.scoring import (
    CalibrationScoreGenerationResult,
    GenerateCalibrationScoresRequest,
    ScoreGenerator,
)
from datp_core.domain.errors import CudaOutOfMemoryError, CudaUnavailableError, ScoringError

if TYPE_CHECKING:
    from datp_core.application.ports.scoring import (
        GenerateTemporalScoresRequest,
        GenerateTestScoresRequest,
        TemporalScoreGenerationResult,
        TestScoreGenerationResult,
    )
    from datp_core.infrastructure.scoring.temporal import TemporalScoreGenerationWorkflow
    from datp_core.infrastructure.scoring.test import TestScoreGenerationWorkflow


class ScoreBatchSink(Protocol):
    def append(self, scores: Tensor) -> None: ...


class CalibrationScoreGenerationWorkflow(Protocol):
    def generate(self, request: GenerateCalibrationScoresRequest) -> CalibrationScoreGenerationResult: ...


@dataclass(slots=True)
class TensorScoreCollector:
    batches: list[Tensor]

    def append(self, scores: Tensor) -> None:
        self.batches.append(scores.detach().cpu())

    def values(self) -> Tensor:
        if not self.batches:
            return torch.empty(0, dtype=torch.float32)
        return torch.cat(self.batches)


@dataclass(frozen=True, slots=True, kw_only=True)
class BatchedCudaReconstructionScorer:
    model: nn.Module
    device: torch.device

    def score(self, *, batches: Iterable[Tensor], sink: ScoreBatchSink) -> int:
        self._require_cuda()
        self.model.eval()
        score_count = 0
        try:
            with torch.no_grad():
                for batch in batches:
                    scores = self._score_batch(batch=batch)
                    sink.append(scores)
                    score_count += scores.numel()
        except torch.OutOfMemoryError as error:
            raise CudaOutOfMemoryError(
                detail="CUDA reconstruction scoring exhausted device memory",
                batch="scoring batch",
                vram=str(torch.cuda.memory_allocated(self.device)),
            ) from error
        return score_count

    def _require_cuda(self) -> None:
        if self.device.type != "cuda" or not torch.cuda.is_available():
            raise CudaUnavailableError(
                detail="reconstruction scoring requires an available CUDA device",
                required_stage="scoring",
            )

    def _score_batch(self, *, batch: Tensor) -> Tensor:
        if batch.ndim != 2:
            raise ScoringError(
                detail="reconstruction scoring requires a rank-two feature batch",
                checkpoint_id="private-model-handle",
                split="private-score-stream",
            )
        device_batch = batch.to(self.device, non_blocking=True)
        reconstruction = self.model(device_batch)
        if reconstruction.shape != device_batch.shape:
            raise ScoringError(
                detail="reconstruction shape must match the input feature batch",
                checkpoint_id="private-model-handle",
                split="private-score-stream",
            )
        return torch.mean(torch.square(reconstruction - device_batch), dim=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class TorchScoreGenerator(ScoreGenerator):
    calibration: CalibrationScoreGenerationWorkflow
    test: "TestScoreGenerationWorkflow"
    temporal: "TemporalScoreGenerationWorkflow"

    def generate_calibration_scores(
        self,
        request: GenerateCalibrationScoresRequest,
    ) -> CalibrationScoreGenerationResult:
        return self.calibration.generate(request)

    def generate_test_scores(self, request: "GenerateTestScoresRequest") -> "TestScoreGenerationResult":
        return self.test.generate(request)

    def generate_temporal_scores(self, request: "GenerateTemporalScoresRequest") -> "TemporalScoreGenerationResult":
        return self.temporal.generate(request)
