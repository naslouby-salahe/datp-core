"""Structural contracts for later execution phases."""

# pylint: disable=too-few-public-methods

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class DatasetReader(Protocol):
    def read(self, path: Path) -> object: ...


@runtime_checkable
class DatasetMaterializer(Protocol):
    def materialize(self, source: Path, destination: Path) -> Path: ...


@runtime_checkable
class PopulationBuilder(Protocol):
    def build(self, dataset: object) -> object: ...


@runtime_checkable
class Preprocessor(Protocol):
    def transform(self, dataset: object) -> object: ...


@runtime_checkable
class Trainer(Protocol):
    def train(self, dataset: object) -> object: ...


@runtime_checkable
class CheckpointSelector(Protocol):
    def select(self, checkpoints: tuple[object, ...]) -> object: ...


@runtime_checkable
class ScoreGenerator(Protocol):
    def score(self, model: object, dataset: object) -> object: ...


@runtime_checkable
class FederatedThresholdEstimator(Protocol):
    def estimate_federated(self, scores: tuple[object, ...]) -> object: ...


@runtime_checkable
class CentralizedThresholdEstimator(Protocol):
    def estimate_centralized(self, scores: object) -> object: ...


@runtime_checkable
class MetricEvaluator(Protocol):
    def evaluate(self, scores: object, threshold: object) -> object: ...


@runtime_checkable
class StageHandler(Protocol):
    def handle_stage(self, stage: str) -> None: ...


@runtime_checkable
class ArtifactSerializer(Protocol):
    def serialize(self, value: object, destination: Path) -> Path: ...


@runtime_checkable
class ArtifactStore(Protocol):
    def load(self, path: Path) -> object: ...


@runtime_checkable
class StageHook(Protocol):
    def after_stage(self, stage: str) -> None: ...
