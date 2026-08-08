from json import loads
from pathlib import Path

import pytest

from datp_core.analysis.evidence import AnalyzeTemporalEvidenceRequest, analyze_temporal_evidence
from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.analysis.temporal import TemporalSeedProvenance, temporal_recovery
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    SplitProtocolId,
    TemporalState,
)
from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT
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
    records = tuple(
        temporal_recovery(
            seed=seed,
            experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            static_reference_cv=MetricValue(0.1),
            frozen_future_cv=MetricValue(0.5),
            recalibrated_future_cv=MetricValue(0.3),
            provenance=_seed_provenance(seed, static=static, frozen=frozen, recalibrated=recalibrated),
        )
        for seed in BOUNDED_EVIDENCE_SEED_COHORT.values
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
    assert len(result.document.records) == len(BOUNDED_EVIDENCE_SEED_COHORT.values)
    document = loads((request.output_directory / "temporal_analysis.json").read_text())
    assert document["campaign_decision"]["decision"] == "supported"
    assert document["threshold_method"] == FederatedThresholdMethod.LOCAL_THRESHOLD.value
    assert "decision" not in document["records"][0]


def test_incomplete_temporal_cohort_cannot_publish_supported(tmp_path: Path) -> None:
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
            provenance=_seed_provenance(Seed(0), static=static, frozen=frozen, recalibrated=recalibrated),
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
        output_directory=tmp_path / "temporal-analysis-incomplete",
        overwrite=False,
    )
    with pytest.raises(ScientificContractError, match="declared seed-cohort"):
        analyze_temporal_evidence(request)


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
        coordinate_checksum=Checksum("9" * 64),
        checkpoint_checksum=Checksum("8" * 64),
        preprocessing_state_set_checksum=Checksum("7" * 64),
        split_manifest_checksum=Checksum("6" * 64),
        calibration_score_set_checksum=Checksum(calibration_checksum),
        evaluation_score_set_checksum=Checksum(evaluation_checksum),
    )


def _seed_provenance(
    seed: Seed,
    *,
    static: TemporalDeploymentProvenance,
    frozen: TemporalDeploymentProvenance,
    recalibrated: TemporalDeploymentProvenance,
) -> TemporalSeedProvenance:
    index = seed.value + 1

    def checksum(tag: str) -> Checksum:
        body = f"{tag}{index:02x}"
        return Checksum((body + "0" * 64)[:64])

    return TemporalSeedProvenance(
        seed=seed,
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        static_reference=static,
        frozen_future=frozen,
        recalibrated_future=recalibrated,
        static_threshold_checksum=checksum("6"),
        frozen_threshold_checksum=checksum("7"),
        recalibrated_threshold_checksum=checksum("8"),
        static_evaluation_checksum=checksum("9"),
        frozen_evaluation_checksum=checksum("0"),
        recalibrated_evaluation_checksum=checksum("f"),
        client_inventory_checksum=checksum("a1"),
        eligibility_checksum=checksum("a2"),
        source_row_checksum=checksum("a3"),
        row_order_checksum=checksum("a4"),
        excluded_clients=(),
        unavailable_reasons=(),
    )
