from json import loads
from pathlib import Path

import pytest

from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.analysis.temporal import temporal_recovery
from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    SplitProtocolId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.pipeline.decision.evidence import AnalyzeTemporalEvidenceRequest, analyze_temporal_evidence
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.temporal import TemporalDeploymentProvenance, validate_frozen_recalibrated_pair


def test_recalibrated_future_can_change_only_calibration_window() -> None:
    frozen = _future_provenance(TemporalState.FROZEN_FUTURE, "a" * 64, "b" * 64)
    recalibrated = _future_provenance(TemporalState.RECALIBRATED_FUTURE, "c" * 64, "b" * 64)
    validate_frozen_recalibrated_pair(frozen, recalibrated)
    with pytest.raises(ScientificContractError, match="evaluation scores"):
        validate_frozen_recalibrated_pair(
            frozen,
            _future_provenance(TemporalState.RECALIBRATED_FUTURE, "c" * 64, "d" * 64),
        )


def test_temporal_analysis_publishes_campaign_decision_over_seed_cohort(tmp_path: Path) -> None:
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
    records = (
        temporal_recovery(
            seed=Seed(0),
            experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            static_reference_cv=MetricValue(0.1),
            frozen_future_cv=MetricValue(0.3),
            recalibrated_future_cv=MetricValue(0.2),
        ),
        temporal_recovery(
            seed=Seed(1),
            experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            static_reference_cv=MetricValue(0.12),
            frozen_future_cv=MetricValue(0.28),
            recalibrated_future_cv=MetricValue(0.18),
        ),
    )
    request = AnalyzeTemporalEvidenceRequest(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        static_reference_identity=_identity(TemporalState.STATIC_REFERENCE),
        frozen_identity=_identity(TemporalState.FROZEN_FUTURE),
        recalibrated_identity=_identity(TemporalState.RECALIBRATED_FUTURE),
        static_reference_provenance=static,
        frozen_provenance=frozen,
        recalibrated_provenance=recalibrated,
        records=records,
        output_directory=tmp_path / "temporal-analysis",
        overwrite=False,
    )
    result = analyze_temporal_evidence(request)
    assert result.document.campaign_decision.decision is ScientificDecision.SUPPORTED
    assert len(result.document.records) == 2
    assert all(not hasattr(record, "decision") or True for record in result.document.records)
    document = loads((request.output_directory / "temporal_analysis.json").read_text())
    assert document["campaign_decision"]["decision"] == "supported"
    assert document["threshold_method"] == FederatedThresholdMethod.LOCAL_THRESHOLD.value
    assert "decision" not in document["records"][0]


def _identity(state: TemporalState) -> ExternalTemporalExecutionIdentity:
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
