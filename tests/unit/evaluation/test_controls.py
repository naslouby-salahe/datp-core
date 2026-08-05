import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.domain.enums import FederatedThresholdMethod, MetricId, PartitionRole
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import AbsoluteTolerance, Checksum, MetricValue, Seed
from datp_core.evaluation.controls import ClientAurocEvidence, FixedScoreEvidence, validate_fixed_score_controls
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import MetricAvailability, MetricReason, MetricStatus


def test_fixed_score_controls_allow_only_threshold_method_to_change() -> None:
    first = _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8))
    second = _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, MetricValue(0.8))

    validate_fixed_score_controls(first, second, auroc_absolute_tolerance=AbsoluteTolerance(1e-12))


def test_fixed_score_controls_reject_changed_auroc() -> None:
    with pytest.raises(ScientificContractError, match="AUROC differs"):
        validate_fixed_score_controls(
            _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8)),
            _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, MetricValue(0.7)),
            auroc_absolute_tolerance=AbsoluteTolerance(1e-12),
        )


def test_fixed_score_controls_allow_matched_unavailable_auroc() -> None:
    unavailable_auroc = unavailable(MetricId.AUROC, MetricStatus.UNAVAILABLE, MetricReason.INVALID_ATTACK_ASSIGNMENT)
    validate_fixed_score_controls(
        _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, unavailable_auroc),
        _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, unavailable_auroc),
        auroc_absolute_tolerance=AbsoluteTolerance(1e-12),
    )


def test_fixed_score_controls_reject_changed_calibration_partition() -> None:
    with pytest.raises(ScientificContractError, match="calibration partition role differs"):
        validate_fixed_score_controls(
            _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8)),
            _evidence(
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                MetricValue(0.8),
                calibration_role=PartitionRole.FUTURE_RECALIBRATION,
            ),
            auroc_absolute_tolerance=AbsoluteTolerance(1e-12),
        )


def _evidence(
    method: FederatedThresholdMethod,
    auroc: MetricValue | MetricAvailability,
    *,
    calibration_role: PartitionRole = PartitionRole.CALIBRATION,
) -> FixedScoreEvidence:
    checksum = Checksum("d" * 64)
    return FixedScoreEvidence(
        coordinate=fedavg_coordinate(Seed(8)),
        threshold_method=method,
        calibration_role=calibration_role,
        model_checksum=checksum,
        preprocessing_checksum=checksum,
        selected_checkpoint_checksum=checksum,
        calibration_score_checksum=checksum,
        evaluation_score_checksum=checksum,
        evaluation_label_checksum=checksum,
        client_population_checksum=checksum,
        eligibility_cohort_checksum=checksum,
        source_row_checksum=checksum,
        score_order_checksum=checksum,
        aurocs=(
            ClientAurocEvidence(
                client_identity("client_a"),
                available(MetricId.AUROC, auroc.value) if isinstance(auroc, MetricValue) else auroc,
            ),
        ),
    )
