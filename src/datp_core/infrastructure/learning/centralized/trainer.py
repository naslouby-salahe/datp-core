from dataclasses import dataclass
from typing import Protocol

from datp_core.application.ports.learning import (
    CentralizedTrainingRunResult,
    TrainCentralizedModelRequest,
)
from datp_core.domain.artifacts.references import ArtifactRef


class CentralizedCheckpointStager(Protocol):
    def stage(self, request: TrainCentralizedModelRequest) -> ArtifactRef: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedTorchTrainer:
    checkpoint_stager: CentralizedCheckpointStager

    def train(self, request: TrainCentralizedModelRequest) -> CentralizedTrainingRunResult:
        return CentralizedTrainingRunResult(
            checkpoint_identity=request.comparator.checkpoint_identity,
            checkpoint_artifact=self.checkpoint_stager.stage(request),
        )
