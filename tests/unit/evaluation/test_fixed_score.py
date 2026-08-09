import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.fixed_score import (
    CalibrationEvidence,
    ClientAurocEvidence,
    DetectorEvidence,
    FixedScoreEvidence,
    HeldOutEvaluationEvidence,
    PopulationEvidence,
)
from datp_core.analysis.metrics.fixed_score_validation import validate_fixed_score_controls
from datp_core.analysis.metrics.models import MetricAvailability, MetricReason, MetricStatus
from datp_core.analysis.metrics.semantics import available, unavailable
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId, PartitionRole
from datp_core.core.numeric import AbsoluteTolerance, MetricValue, Seed


def test_fixed_score_controls_allow_only_threshold_method_to_change() -> None:
    first = _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8))
    second = _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, MetricValue(0.8))

    validate_fixed_score_controls(first, second, auroc_absolute_tolerance=AbsoluteTolerance(1e-12))


def test_fixed_score_controls_reject_changed_auroc() -> None:
    first = _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8))
    second = _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, MetricValue(0.7))
    tolerance = AbsoluteTolerance(1e-12)
    with pytest.raises(ScientificContractError, match="AUROC differs"):
        validate_fixed_score_controls(first, second, auroc_absolute_tolerance=tolerance)


def test_fixed_score_controls_allow_matched_unavailable_auroc() -> None:
    unavailable_auroc = unavailable(MetricId.AUROC, MetricStatus.UNAVAILABLE, MetricReason.INVALID_ATTACK_ASSIGNMENT)
    validate_fixed_score_controls(
        _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, unavailable_auroc),
        _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, unavailable_auroc),
        auroc_absolute_tolerance=AbsoluteTolerance(1e-12),
    )


def test_fixed_score_controls_reject_changed_calibration_partition() -> None:
    first = _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8))
    second = _evidence(
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        MetricValue(0.8),
        calibration_role=PartitionRole.FUTURE_RECALIBRATION,
    )
    tolerance = AbsoluteTolerance(1e-12)
    with pytest.raises(ScientificContractError, match="calibration partition role differs"):
        validate_fixed_score_controls(first, second, auroc_absolute_tolerance=tolerance)


def test_calibration_evidence_rejects_non_calibration_role() -> None:
    checksum = Checksum("a" * 64)
    with pytest.raises(ValueError, match="calibration partition role"):
        CalibrationEvidence(role=PartitionRole.EVALUATION, score_checksum=checksum)


def test_held_out_evidence_rejects_duplicate_auroc_clients() -> None:
    item = ClientAurocEvidence(client_identity("client_a"), available(MetricId.AUROC, 0.8))
    score_checksum = Checksum("a" * 64)
    label_checksum = Checksum("b" * 64)
    source_row_checksum = Checksum("c" * 64)
    score_order_checksum = Checksum("d" * 64)
    with pytest.raises(ValueError, match="unique by client"):
        HeldOutEvaluationEvidence(
            score_checksum=score_checksum,
            label_checksum=label_checksum,
            source_row_checksum=source_row_checksum,
            score_order_checksum=score_order_checksum,
            aurocs=(item, item),
        )


def _evidence(
    method: FederatedThresholdMethod,
    auroc: MetricValue | MetricAvailability,
    *,
    calibration_role: PartitionRole = PartitionRole.CALIBRATION,
) -> FixedScoreEvidence:
    checksum = Checksum("d" * 64)
    return FixedScoreEvidence(
        threshold_method=method,
        detector=DetectorEvidence(
            coordinate=fedavg_coordinate(Seed(8)),
            model_checksum=checksum,
            preprocessing_checksum=checksum,
            selected_checkpoint_checksum=checksum,
        ),
        calibration=CalibrationEvidence(role=calibration_role, score_checksum=checksum),
        evaluation=HeldOutEvaluationEvidence(
            score_checksum=checksum,
            label_checksum=checksum,
            source_row_checksum=checksum,
            score_order_checksum=checksum,
            aurocs=(
                ClientAurocEvidence(
                    client_identity("client_a"),
                    available(MetricId.AUROC, auroc.value) if isinstance(auroc, MetricValue) else auroc,
                ),
            ),
        ),
        population=PopulationEvidence(
            client_inventory_checksum=checksum,
            eligibility_cohort_checksum=checksum,
        ),
    )
