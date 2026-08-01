import pytest

from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    TemporalInterpretation,
    temporal_recovery,
    validate_frozen_recalibrated_pair,
)
from datp_core.domain.enums import PartitionRole, SplitProtocolId, TemporalState
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, Seed


def test_one_shot_recalibration_uses_one_future_evaluation_trajectory() -> None:
    result = temporal_recovery(
        seed=Seed(1),
        static_reference_cv=MetricValue(0.1),
        frozen_future_cv=MetricValue(0.3),
        recalibrated_future_cv=MetricValue(0.2),
    )
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY


def test_recalibrated_future_can_change_only_its_calibration_window() -> None:
    frozen = _future_provenance(TemporalState.FROZEN_FUTURE, "a" * 64, "b" * 64)
    recalibrated = _future_provenance(TemporalState.RECALIBRATED_FUTURE, "c" * 64, "b" * 64)
    validate_frozen_recalibrated_pair(frozen, recalibrated)

    with pytest.raises(ScientificContractError, match="future evaluation scores"):
        validate_frozen_recalibrated_pair(
            frozen,
            _future_provenance(TemporalState.RECALIBRATED_FUTURE, "c" * 64, "d" * 64),
        )


def _future_provenance(
    state: TemporalState,
    calibration_checksum: str,
    evaluation_checksum: str,
) -> TemporalDeploymentProvenance:
    return TemporalDeploymentProvenance(
        state=state,
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        calibration_role=(
            PartitionRole.CALIBRATION if state is TemporalState.FROZEN_FUTURE else PartitionRole.FUTURE_RECALIBRATION
        ),
        evaluation_role=PartitionRole.EVALUATION,
        coordinate_checksum=Checksum("e" * 64),
        checkpoint_checksum=Checksum("f" * 64),
        preprocessing_state_set_checksum=Checksum("1" * 64),
        split_manifest_checksum=Checksum("2" * 64),
        calibration_score_set_checksum=Checksum(calibration_checksum),
        evaluation_score_set_checksum=Checksum(evaluation_checksum),
    )
