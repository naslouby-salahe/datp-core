from dataclasses import dataclass
from typing import Protocol

from datp_core.domain.data.datasets import DatasetSourceInspectionResult, DatasetSpec
from datp_core.domain.data.partitioning import ClientPartitionResult, ClientPartitionSpec
from datp_core.domain.data.preprocessing import (
    FittedPreprocessorResult,
    PreprocessingSpec,
    ProcessedSplitResult,
)
from datp_core.domain.data.splitting import SplitCollectionSpec, SplitManifestResult


@dataclass(frozen=True, slots=True, kw_only=True)
class InspectDatasetSourceRequest:
    dataset: DatasetSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientPartitionRequest:
    inspection: DatasetSourceInspectionResult
    partitioning: ClientPartitionSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildSplitManifestRequest:
    partition: ClientPartitionResult
    splits: SplitCollectionSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class FitPreprocessorRequest:
    split_manifest: SplitManifestResult
    preprocessing: PreprocessingSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializeProcessedSplitsRequest:
    split_manifest: SplitManifestResult
    fitted_preprocessor: FittedPreprocessorResult


class DatasetSourceInspector(Protocol):
    def inspect(self, request: InspectDatasetSourceRequest) -> DatasetSourceInspectionResult: ...


class ClientPartitioner(Protocol):
    def partition(self, request: ClientPartitionRequest) -> ClientPartitionResult: ...


class SplitManifestBuilder(Protocol):
    def build(self, request: BuildSplitManifestRequest) -> SplitManifestResult: ...


class PreprocessorFitter(Protocol):
    def fit(self, request: FitPreprocessorRequest) -> FittedPreprocessorResult: ...


class ProcessedSplitMaterializer(Protocol):
    def materialize(self, request: MaterializeProcessedSplitsRequest) -> ProcessedSplitResult: ...
