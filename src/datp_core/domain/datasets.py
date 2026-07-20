"""Domain models for dataset schemas, layout definitions, and setup specifications."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .identifiers import DatasetId, DatasetSetupId
from .values import PositiveInt, RelativePath


class DatasetKind(Enum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureSchema:
    source_column_count: PositiveInt
    model_feature_names: tuple[str, ...]
    label_column_name: str
    client_id_derivation: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetLayoutSpec:
    dataset_id: DatasetId
    root_relative_path: RelativePath
    benign_file_pattern: str
    attack_file_pattern: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSetupSpec:
    identifier: DatasetSetupId
    dataset_id: DatasetId
    description: str
    split_ratios: tuple[float, float, float]  # train, calibration, test
