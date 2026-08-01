import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.domain.enums import FederatedThresholdMethod, MetricId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.evaluation.controls import ClientAurocEvidence, FixedScoreEvidence, validate_fixed_score_controls
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import MetricAvailability, MetricReason, MetricStatus


def test_fixed_score_controls_allow_only_threshold_method_to_change() -> None:
    first = _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8))
    second = _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, MetricValue(0.8))

    validate_fixed_score_controls(first, second, auroc_absolute_tolerance=0.0)


def test_fixed_score_controls_reject_changed_auroc() -> None:
    with pytest.raises(ScientificContractError, match="AUROC differs"):
        validate_fixed_score_controls(
            _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, MetricValue(0.8)),
            _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, MetricValue(0.7)),
            auroc_absolute_tolerance=0.0,
        )


def test_fixed_score_controls_allow_matched_unavailable_auroc() -> None:
    unavailable_auroc = unavailable(MetricId.AUROC, MetricStatus.UNAVAILABLE, MetricReason.INVALID_ATTACK_ASSIGNMENT)
    validate_fixed_score_controls(
        _evidence(FederatedThresholdMethod.SHARED_THRESHOLD, unavailable_auroc),
        _evidence(FederatedThresholdMethod.LOCAL_THRESHOLD, unavailable_auroc),
        auroc_absolute_tolerance=0.0,
    )


def _evidence(method: FederatedThresholdMethod, auroc: MetricValue | MetricAvailability) -> FixedScoreEvidence:
    checksum = Checksum("d" * 64)
    return FixedScoreEvidence(
        fedavg_coordinate(Seed(8)),
        method,
        checksum,
        checksum,
        checksum,
        checksum,
        checksum,
        checksum,
        checksum,
        checksum,
        checksum,
        checksum,
        (
            ClientAurocEvidence(
                client_identity("client_a"),
                available(MetricId.AUROC, auroc.value) if isinstance(auroc, MetricValue) else auroc,
            ),
        ),
    )
