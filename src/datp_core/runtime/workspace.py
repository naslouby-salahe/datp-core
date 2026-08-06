"""Typed repository workspace for data, output, and result artifacts."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import DatasetId, RawDatasetDirectory, ReusableDataCoordinateKind

from .configuration import CANONICAL_RUNTIME, RuntimeConfiguration


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactWorkspace:
    configuration: RuntimeConfiguration

    @property
    def data_root(self) -> Path:
        return self.configuration.layout.data_root

    @property
    def outputs_root(self) -> Path:
        return self.configuration.layout.outputs_root

    @property
    def results_root(self) -> Path:
        return self.configuration.layout.results_root

    def raw_dataset_root(self, dataset: DatasetId) -> Path:
        return self.data_root / ReusableDataCoordinateKind.RAW / RawDatasetDirectory[dataset.name].value

    def canonical_dataset_root(self, dataset: DatasetId) -> Path:
        return self.data_root / ReusableDataCoordinateKind.CANONICAL / dataset.value

    def output_path(self, *segments: str) -> Path:
        return self.outputs_root.joinpath(*segments)

    def result_path(self, *segments: str) -> Path:
        return self.results_root.joinpath(*segments)


CANONICAL_WORKSPACE = ArtifactWorkspace(configuration=CANONICAL_RUNTIME)
