from datp_core.domain.learning.checkpoints import CheckpointKind, CheckpointSelectionStrategy
from datp_core.domain.learning.models import ActivationFunction
from datp_core.domain.learning.scores import QuantileEstimatorType
from datp_core.domain.learning.training import (
    AggregationStrategy,
    DeterminismLevel,
    LrSchedulerType,
    ModelPersonalizationStrategy,
    OptimizerType,
    ParticipationStrategy,
    PrecisionMode,
)


def test_model_and_training_vocabulary_has_stable_serialized_values() -> None:
    assert tuple(ActivationFunction) == (
        ActivationFunction.RELU,
        ActivationFunction.LEAKY_RELU,
        ActivationFunction.TANH,
        ActivationFunction.SIGMOID,
        ActivationFunction.ELU,
    )
    assert tuple(AggregationStrategy) == (AggregationStrategy.FEDAVG, AggregationStrategy.FEDPROX)
    assert tuple(OptimizerType) == (OptimizerType.ADAM, OptimizerType.ADAMW, OptimizerType.SGD, OptimizerType.RMSPROP)
    assert tuple(LrSchedulerType) == (
        LrSchedulerType.NONE,
        LrSchedulerType.STEP,
        LrSchedulerType.COSINE,
        LrSchedulerType.PLATEAU,
    )
    assert tuple(PrecisionMode) == (
        PrecisionMode.FP32,
        PrecisionMode.TF32,
        PrecisionMode.MIXED_FP16,
        PrecisionMode.MIXED_BF16,
    )
    assert tuple(DeterminismLevel) == (DeterminismLevel.STRICT, DeterminismLevel.RELAXED)


def test_checkpoint_and_participation_vocabulary_are_closed() -> None:
    assert tuple(CheckpointKind) == (CheckpointKind.SCIENTIFIC, CheckpointKind.RECOVERY)
    assert tuple(CheckpointSelectionStrategy) == (CheckpointSelectionStrategy.REGIME_A_GLOBAL_PRIMARY,)
    assert tuple(ParticipationStrategy) == (ParticipationStrategy.FULL,)


def test_personalization_vocabulary_preserves_distinct_algorithm_names() -> None:
    assert tuple(ModelPersonalizationStrategy) == (
        ModelPersonalizationStrategy.NONE,
        ModelPersonalizationStrategy.DITTO,
        ModelPersonalizationStrategy.FEDREP_AE,
        ModelPersonalizationStrategy.FEDPER_AE,
    )
    assert ModelPersonalizationStrategy.FEDREP_AE is not ModelPersonalizationStrategy.DITTO
    assert ModelPersonalizationStrategy.FEDPER_AE is not ModelPersonalizationStrategy.DITTO


def test_quantile_vocabulary_contains_only_exact_estimators() -> None:
    assert tuple(QuantileEstimatorType) == (
        QuantileEstimatorType.LOCAL_EXACT,
        QuantileEstimatorType.POOLED_EXACT,
        QuantileEstimatorType.WEIGHTED_EXACT,
        QuantileEstimatorType.CENTRALIZED_ORACLE,
    )
    assert all(
        "exact" in estimator.value or estimator is QuantileEstimatorType.CENTRALIZED_ORACLE
        for estimator in QuantileEstimatorType
    )
