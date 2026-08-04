"""Typed canonical-dataset materialization commands and outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.datasets.models import DatasetMaterializationResult
from datp_core.domain.enums import DatasetId, StageOperationId


@dataclass(frozen=True, slots=True)
class MaterializeCanonicalDatasetsRequest:
    data_root: Path
    datasets: tuple[DatasetId, ...]


@dataclass(frozen=True, slots=True)
class MaterializeCanonicalDatasetsResult:
    stage: ClassVar[StageOperationId] = StageOperationId.MATERIALIZE_CANONICAL_DATASETS
    publications: tuple[DatasetMaterializationResult, ...]
