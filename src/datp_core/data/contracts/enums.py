"""Authoritative enums for the data package — one source of truth for every closed domain concept."""

from __future__ import annotations

from enum import Enum, StrEnum


class AdapterKind(Enum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


class SplitMethod(StrEnum):
    RANDOM_FRACTIONAL = "random_fractional"
    CHRONOLOGICAL_GAPPED = "chronological_gapped"
    WITHIN_CLIENT_CHRONOLOGICAL = "within_client_chronological"


class SplitMembership(Enum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    TEST = "test"
    EXCLUDED_GAP = "excluded_gap"
    RECALIBRATION_REFERENCE = "recalibration_reference"
    HISTORICAL_TRAINING = "historical_training"
    HISTORICAL_CALIBRATION = "historical_calibration"
    FUTURE_RECALIBRATION = "future_recalibration"
    FUTURE_EVALUATION = "future_evaluation"


class ClientConstructionMethod(StrEnum):
    DATASET_FILE_PSEUDO_CLIENTS = "dataset_file_pseudo_clients"
    DIRICHLET_PARTITIONED_CLIENTS = "dirichlet_partitioned_clients"
    PHYSICAL_DEVICE_CLIENTS = "physical_device_clients"
    SENSOR_GROUP_CLIENTS = "sensor_group_clients"


class NormalizationStrategy(StrEnum):
    MIN_MAX = "min_max"
    STANDARD = "standard"


class NormalizationFitScope(StrEnum):
    GLOBAL_TRAIN = "global_train"
    PER_CLIENT_TRAIN = "per_client_train"
    HISTORICAL_TRAIN = "historical_train"
