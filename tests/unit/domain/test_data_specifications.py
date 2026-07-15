from dataclasses import fields
from decimal import Decimal

import pytest

from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity, TemporalWindowIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.datasets import Regime, TimestampEvidence, TimestampEvidenceKind
from datp_core.domain.data.partitioning import (
    ClientDefinitionStrategy,
    ClientPartitionSpec,
    DirichletAlpha,
    DirichletPartitionSpec,
    NaturalDevicePartitionSpec,
)
from datp_core.domain.data.splitting import (
    BenignCalibrationSplitSpec,
    ConformalQuantileIndexRule,
    ConformalSplitSpec,
    HistoricalTemporalWindowSpec,
    OneShotRecalibrationSpec,
    RecalibrationMode,
    SplitCollectionSpec,
    TemporalBoundary,
    TemporalEvaluationWindowSpec,
    TemporalProtocolSpec,
    TestSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.statistical_results import Probability
from datp_core.domain.thresholding.policies import FprTarget, ThresholdPercentile


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _partition() -> PartitionIdentity:
    return PartitionIdentity(value=_fingerprint("a"))


def _training() -> TrainingSplitSpec:
    return TrainingSplitSpec(split_identity=SplitIdentity(value=_fingerprint("b")), partition_identity=_partition())


def _calibration() -> BenignCalibrationSplitSpec:
    return BenignCalibrationSplitSpec(
        split_identity=SplitIdentity(value=_fingerprint("c")),
        partition_identity=_partition(),
    )


def _test() -> TestSplitSpec:
    return TestSplitSpec(split_identity=SplitIdentity(value=_fingerprint("d")), partition_identity=_partition())


def test_split_roles_are_constructor_locked_and_calibration_has_no_attack_admitting_field() -> None:
    calibration_fields = {entry.name for entry in fields(BenignCalibrationSplitSpec)}
    split_identity = SplitIdentity(value=_fingerprint("e"))
    partition_identity = _partition()

    assert calibration_fields == {"split_identity", "partition_identity", "role"}
    with pytest.raises(TypeError):
        type.__call__(
            BenignCalibrationSplitSpec,
            split_identity=split_identity,
            partition_identity=partition_identity,
            role="attack",
        )


def test_conformal_specification_rejects_test_split_in_each_threshold_fit_position() -> None:
    test_split = _test()
    percentile = ThresholdPercentile(value=Decimal("0.95"))
    alpha = FprTarget.from_percentile(percentile=percentile)
    calibration_split = _calibration()
    training_split = _training()

    with pytest.raises(DomainValidationError):
        type.__call__(
            ConformalSplitSpec,
            proper_fit_split=test_split,
            calibration_split=calibration_split,
            percentile=percentile,
            alpha=alpha,
            quantile_index_rule=ConformalQuantileIndexRule.CEILING_N_PLUS_ONE,
        )
    with pytest.raises(DomainValidationError):
        type.__call__(
            ConformalSplitSpec,
            proper_fit_split=training_split,
            calibration_split=test_split,
            percentile=percentile,
            alpha=alpha,
            quantile_index_rule=ConformalQuantileIndexRule.CEILING_N_PLUS_ONE,
        )


def test_temporal_boundary_is_locked_to_genuine_capture_time_at_exactly_seventy_percent() -> None:
    evidence = TimestampEvidence(
        kind=TimestampEvidenceKind.GENUINE_CAPTURE_TIME,
        capture_timestamp_field="captured_at",
    )
    boundary = TemporalBoundary(
        historical_fraction=Probability(value=Decimal("0.70")),
        timestamp_field=evidence,
        boundary_identity=TemporalWindowIdentity(value=_fingerprint("e")),
    )

    protocol = TemporalProtocolSpec(
        historical=HistoricalTemporalWindowSpec(boundary=boundary),
        evaluation=TemporalEvaluationWindowSpec(boundary=boundary),
        one_shot_recalibration=OneShotRecalibrationSpec(
            mode=RecalibrationMode.ONE_SHOT,
            calibration_split=_calibration(),
        ),
    )
    invalid_fraction = Probability(value=Decimal("0.69"))
    invalid_boundary_identity = TemporalWindowIdentity(value=_fingerprint("f"))

    assert protocol.historical.boundary.historical_fraction.value == Decimal("0.700000000000")
    with pytest.raises(DomainValidationError):
        TemporalBoundary(
            historical_fraction=invalid_fraction,
            timestamp_field=evidence,
            boundary_identity=invalid_boundary_identity,
        )
    with pytest.raises(DomainValidationError):
        TimestampEvidence(kind=TimestampEvidenceKind.GENUINE_CAPTURE_TIME, capture_timestamp_field="file_order")


def test_partition_strategies_are_closed_and_dirichlet_fields_are_isolated() -> None:
    natural = NaturalDevicePartitionSpec(strategy=ClientDefinitionStrategy.NATURAL_DEVICE, regime=Regime.A)
    dirichlet = DirichletPartitionSpec(
        strategy=ClientDefinitionStrategy.DIRICHLET_SYNTHETIC,
        regime=Regime.A,
        alpha=DirichletAlpha(value=0.5),
    )

    assert {entry.name for entry in fields(natural)} == {"strategy", "regime"}
    assert {entry.name for entry in fields(dirichlet)} == {"strategy", "regime", "alpha"}
    with pytest.raises(TypeError):
        type.__call__(ClientPartitionSpec, strategy=ClientDefinitionStrategy.NATURAL_DEVICE, regime=Regime.A)


def test_split_collection_requires_one_distinct_split_for_every_static_role() -> None:
    collection = SplitCollectionSpec(training=_training(), calibration=_calibration(), test=_test())
    duplicate_training = _training()
    duplicate_calibration = BenignCalibrationSplitSpec(
        split_identity=SplitIdentity(value=_fingerprint("b")), partition_identity=_partition()
    )
    duplicate_test = _test()

    assert tuple(type(split) for split in (collection.training, collection.calibration, collection.test)) == (
        TrainingSplitSpec,
        BenignCalibrationSplitSpec,
        TestSplitSpec,
    )
    with pytest.raises(DomainValidationError):
        SplitCollectionSpec(
            training=duplicate_training,
            calibration=duplicate_calibration,
            test=duplicate_test,
        )
