"""Authoritative enums for the learning package — closed-domain training, scoring, and checkpoint concepts."""

from __future__ import annotations

from enum import StrEnum


class TrainingProfileKind(StrEnum):
    CENTRALIZED_POOLED_TRAINING = "centralized_pooled_training"
    DENSE_AUTOENCODER = "dense_autoencoder"
    FEDERATED_AVERAGING_TRAINING = "federated_averaging_training"
    FEDERATED_PROX_TRAINING = "federated_prox_training"


class PersonalizationStrategy(StrEnum):
    NONE = "none"
    DITTO = "ditto"


class CheckpointAuthorization(StrEnum):
    PRIMARY_SELECTION_COMPUTED_ONCE = "primary_selection_computed_once_on_natural_device_regime"
    LOOKUP_OF_FEDERATED_AVERAGING = "lookup_of_federated_averaging_primary_selection"
    HISTORICAL_FIRST_QUALIFYING_ROUND = "historical_first_qualifying_round_or_150_round_cap"
    INDEPENDENT_SELECTION = (
        "independent_selection_own_non_federated_curve_never_fused_with_federated_averaging_artifacts"
    )


class TrainingParticipation(StrEnum):
    FULL = "full"


class ScoreOrientation(StrEnum):
    HIGHER_MORE_ANOMALOUS = "higher_score_means_more_anomalous"


class ModelArchitectureKind(StrEnum):
    DENSE_AUTOENCODER = "dense_autoencoder"


class ActivationKind(StrEnum):
    RELU = "relu"


class OptimizerKind(StrEnum):
    ADAM = "adam"


class DevicePolicy(StrEnum):
    CUDA_REQUIRED = "cuda_required"
