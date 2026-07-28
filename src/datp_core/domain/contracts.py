"""Structural contracts for later execution phases."""

# pylint: disable=too-few-public-methods

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class DatasetReader[DatasetContract](Protocol):
    def read(self, path: Path) -> DatasetContract: ...


@runtime_checkable
class DatasetMaterializer[SourceDatasetContract, MaterializedDatasetContract](Protocol):
    def materialize(self, source: SourceDatasetContract, destination: Path) -> MaterializedDatasetContract: ...


@runtime_checkable
class PopulationBuilder[DatasetContract, PopulationContract](Protocol):
    def build(self, dataset: DatasetContract) -> PopulationContract: ...


@runtime_checkable
class Preprocessor[DatasetContract, ProcessedDatasetContract](Protocol):
    def transform(self, dataset: DatasetContract) -> ProcessedDatasetContract: ...


@runtime_checkable
class Trainer[DatasetContract, ModelContract](Protocol):
    def train(self, dataset: DatasetContract) -> ModelContract: ...


@runtime_checkable
class CheckpointSelector[CheckpointContract](Protocol):
    def select(self, checkpoints: tuple[CheckpointContract, ...]) -> CheckpointContract: ...


@runtime_checkable
class ScoreGenerator[ModelContract, DatasetContract, ScoreSetContract](Protocol):
    def score(self, model: ModelContract, dataset: DatasetContract) -> ScoreSetContract: ...


@runtime_checkable
class FederatedThresholdEstimator[ScoreSetContract, ThresholdContract](Protocol):
    def estimate_federated(self, scores: tuple[ScoreSetContract, ...]) -> ThresholdContract: ...


@runtime_checkable
class CentralizedThresholdEstimator[ScoreSetContract, ThresholdContract](Protocol):
    def estimate_centralized(self, scores: ScoreSetContract) -> ThresholdContract: ...


@runtime_checkable
class MetricEvaluator[ScoreSetContract, ThresholdContract, MetricResultContract](Protocol):
    def evaluate(self, scores: ScoreSetContract, threshold: ThresholdContract) -> MetricResultContract: ...


@runtime_checkable
class StageHandler[StageContract](Protocol):
    def handle_stage(self, stage: StageContract) -> None: ...


@runtime_checkable
class ArtifactSerializer[ArtifactContract](Protocol):
    def serialize(self, value: ArtifactContract, destination: Path) -> Path: ...


@runtime_checkable
class ArtifactStore[ArtifactContract](Protocol):
    def load(self, path: Path) -> ArtifactContract: ...


@runtime_checkable
class StageHook[StageContract](Protocol):
    def after_stage(self, stage: StageContract) -> None: ...
