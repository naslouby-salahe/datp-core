from pathlib import Path

import pytest

from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    TemporalInterpretation,
    temporal_recovery,
    validate_frozen_recalibrated_pair,
)
from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    PartitionRole,
    PopulationId,
    SplitProtocolId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.orchestration.stages.analyze import TemporalAnalyzeRequest, analyze_temporal_stage


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

    with pytest.raises(ScientificContractError, match="evaluation scores"):
        validate_frozen_recalibrated_pair(
            frozen,
            _future_provenance(TemporalState.RECALIBRATED_FUTURE, "c" * 64, "d" * 64),
        )


def test_temporal_analysis_publishes_all_three_states_without_a_decision(tmp_path: Path) -> None:
    frozen = _future_provenance(TemporalState.FROZEN_FUTURE, "1" * 64, "2" * 64)
    recalibrated = _future_provenance(TemporalState.RECALIBRATED_FUTURE, "3" * 64, "2" * 64)
    static = TemporalDeploymentProvenance(
        state=TemporalState.STATIC_REFERENCE,
        split_protocol=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
        calibration_role=PartitionRole.CALIBRATION,
        evaluation_role=PartitionRole.EVALUATION,
        coordinate_checksum=frozen.coordinate_checksum,
        checkpoint_checksum=frozen.checkpoint_checksum,
        preprocessing_state_set_checksum=frozen.preprocessing_state_set_checksum,
        split_manifest_checksum=Checksum("4" * 64),
        calibration_score_set_checksum=Checksum("5" * 64),
        evaluation_score_set_checksum=Checksum("6" * 64),
    )
    result = analyze_temporal_stage(
        TemporalAnalyzeRequest(
            static_reference_identity=_temporal_identity(TemporalState.STATIC_REFERENCE),
            frozen_identity=_temporal_identity(TemporalState.FROZEN_FUTURE),
            recalibrated_identity=_temporal_identity(TemporalState.RECALIBRATED_FUTURE),
            static_reference_provenance=static,
            frozen_provenance=frozen,
            recalibrated_provenance=recalibrated,
            records=(
                temporal_recovery(
                    seed=Seed(1),
                    static_reference_cv=MetricValue(0.1),
                    frozen_future_cv=MetricValue(0.3),
                    recalibrated_future_cv=MetricValue(0.2),
                ),
            ),
            output_directory=tmp_path / "temporal-analysis",
            overwrite=False,
        )
    )
    assert result.records[0].interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY
    assert (tmp_path / "temporal-analysis" / "temporal_analysis.json").is_file()
    assert "decision" not in (tmp_path / "temporal-analysis" / "temporal_analysis.json").read_text()


def _temporal_identity(state: TemporalState) -> ExternalTemporalExecutionIdentity:
    return ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=state,
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
