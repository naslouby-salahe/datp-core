"""Closed-domain learning concepts."""

from __future__ import annotations

from enum import StrEnum


class ModelArchitectureKind(StrEnum):
    DENSE_AUTOENCODER = "dense_autoencoder"


class ActivationKind(StrEnum):
    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    GELU = "gelu"
    ELU = "elu"


class OutputActivationKind(StrEnum):
    IDENTITY = "identity"
    SIGMOID = "sigmoid"
    TANH = "tanh"


class NormalizationKind(StrEnum):
    NONE = "none"
    BATCH_NORMALIZATION = "batch_normalization"
    LAYER_NORMALIZATION = "layer_normalization"


class ReconstructionObjective(StrEnum):
    MEAN_SQUARED_ERROR = "mean_squared_error"
    MEAN_ABSOLUTE_ERROR = "mean_absolute_error"
    HUBER = "huber"


class LossReduction(StrEnum):
    MEAN = "mean"
    SUM = "sum"


class PrecisionKind(StrEnum):
    FLOAT32 = "float32"
    FLOAT64 = "float64"


class WeightInitializationKind(StrEnum):
    KAIMING_UNIFORM = "kaiming_uniform"
    XAVIER_UNIFORM = "xavier_uniform"


class BiasInitializationKind(StrEnum):
    ZERO = "zero"


class OptimizerKind(StrEnum):
    ADAM = "adam"


class OptimizerStateLifecycle(StrEnum):
    RESET_EACH_LOCAL_TRAINING = "reset_each_local_training"


class SchedulerKind(StrEnum):
    NONE = "none"
    STEP = "step"


class GradientClippingKind(StrEnum):
    NONE = "none"
    GLOBAL_NORM = "global_norm"


class ShufflePolicy(StrEnum):
    EACH_EPOCH = "each_epoch"
    DISABLED = "disabled"


class IncompleteBatchPolicy(StrEnum):
    KEEP = "keep"
    DROP = "drop"


class AccumulationRemainderPolicy(StrEnum):
    STEP_PARTIAL = "step_partial"
    DROP_PARTIAL = "drop_partial"


class TrainingAlgorithm(StrEnum):
    CENTRALIZED = "centralized"
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"
    DITTO = "ditto"


class ParticipationPolicy(StrEnum):
    FULL = "full"


class CheckpointAuthorization(StrEnum):
    INDEPENDENT_SELECTION = "independent_selection"
    PRIMARY_SELECTION = "primary_selection"
    FEDAVG_SELECTION_LOOKUP = "fedavg_selection_lookup"


class CheckpointSelectionKind(StrEnum):
    FIRST_QUALIFYING_CONVERGENCE = "first_qualifying_convergence"
    LOWEST_CALIBRATION_LOSS = "lowest_calibration_loss"
    FIXED_ROUND = "fixed_round"
    AUTHORIZED_LOOKUP = "authorized_lookup"


class CheckpointTieBreak(StrEnum):
    EARLIEST_ROUND = "earliest_round"
    LATEST_ROUND = "latest_round"


class NoQualifyingRoundPolicy(StrEnum):
    FINAL_ROUND = "final_round"
    FAIL = "fail"


class CheckpointSavePolicy(StrEnum):
    CONFIGURED_ROUNDS = "configured_rounds"


class DevicePolicy(StrEnum):
    CUDA_REQUIRED = "cuda_required"


class CudnnBenchmarkPolicy(StrEnum):
    DISABLED = "disabled"


class CublasWorkspaceConfiguration(StrEnum):
    DETERMINISTIC_16_8 = ":16:8"
    DETERMINISTIC_4096_8 = ":4096:8"


class ScoreOrientation(StrEnum):
    HIGHER_MORE_ANOMALOUS = "higher_more_anomalous"


class ScoreArtifactKind(StrEnum):
    CALIBRATION_SCORES = "calibration_scores"
    FUTURE_RECALIBRATION_SCORES = "future_recalibration_scores"
    TEST_SCORES = "test_scores"


class LearningArtifactKind(StrEnum):
    MATERIALIZATION = "materialization"
    CHECKPOINT = "checkpoint"
    PERSONALIZED_CHECKPOINT = "personalized_checkpoint"
    SELECTION_EVIDENCE = "selection_evidence"
    CHECKPOINT_SELECTION = "checkpoint_selection"


class CheckpointStateKind(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


class LoaderBranch(StrEnum):
    CENTRALIZED = "centralized"
    GLOBAL = "global"
    PERSONALIZED = "personalized"


class SplitProfileKind(StrEnum):
    STANDARD = "standard"
    TEMPORAL = "temporal"


class SeedAnalysisModel(StrEnum):
    PAIRED = "paired"
