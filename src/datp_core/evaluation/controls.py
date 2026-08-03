"""Machine-verifiable fixed-score controls for threshold-policy comparisons."""

from dataclasses import dataclass

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod, MetricId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import AbsoluteTolerance, Checksum, floats_absolutely_close
from datp_core.evaluation.models import MetricAvailability, MetricStatus
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


@dataclass(frozen=True, slots=True)
class ClientAurocEvidence:
    client: ClientIdentity
    outcome: MetricAvailability

    def __post_init__(self) -> None:
        if self.outcome.metric is not MetricId.AUROC:
            raise ValueError("AUROC evidence must carry the AUROC metric")


@dataclass(frozen=True, slots=True)
class FixedScoreEvidence:
    """Checksummed evidence which must be invariant across threshold methods."""

    coordinate: FederatedTrainingCoordinate
    threshold_method: FederatedThresholdMethod
    model_checksum: Checksum
    preprocessing_checksum: Checksum
    selected_checkpoint_checksum: Checksum
    calibration_score_checksum: Checksum
    evaluation_score_checksum: Checksum
    evaluation_label_checksum: Checksum
    client_population_checksum: Checksum
    eligibility_cohort_checksum: Checksum
    source_row_checksum: Checksum
    score_order_checksum: Checksum
    aurocs: tuple[ClientAurocEvidence, ...]

    def __post_init__(self) -> None:
        clients = tuple(item.client for item in self.aurocs)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("AUROC evidence must be unique by client")


def validate_fixed_score_controls(
    first: FixedScoreEvidence,
    second: FixedScoreEvidence,
    *,
    auroc_absolute_tolerance: AbsoluteTolerance,
) -> None:
    """Reject every changed fixed input; threshold policy is the sole permitted difference."""
    if first.threshold_method is second.threshold_method:
        raise ScientificContractError(
            "fixed-score comparison requires distinct threshold methods", subject=ContractSubject.THRESHOLD_METHOD
        )
    _require_equal(first.coordinate, second.coordinate, ContractSubject.COORDINATE, "training coordinate")
    _require_equal(first.model_checksum, second.model_checksum, ContractSubject.SCORES, "model checksum")
    _require_equal(
        first.preprocessing_checksum,
        second.preprocessing_checksum,
        ContractSubject.PREPROCESSING,
        "preprocessing checksum",
    )
    _require_equal(
        first.selected_checkpoint_checksum,
        second.selected_checkpoint_checksum,
        ContractSubject.CHECKPOINT_CANDIDATES,
        "selected-checkpoint checksum",
    )
    _require_equal(
        first.calibration_score_checksum,
        second.calibration_score_checksum,
        ContractSubject.SCORES,
        "calibration-score checksum",
    )
    _require_equal(
        first.evaluation_score_checksum,
        second.evaluation_score_checksum,
        ContractSubject.SCORES,
        "evaluation-score checksum",
    )
    _require_equal(
        first.evaluation_label_checksum,
        second.evaluation_label_checksum,
        ContractSubject.LABEL,
        "evaluation-label checksum",
    )
    _require_equal(
        first.client_population_checksum,
        second.client_population_checksum,
        ContractSubject.CLIENT_IDENTITY,
        "client population",
    )
    _require_equal(
        first.eligibility_cohort_checksum,
        second.eligibility_cohort_checksum,
        ContractSubject.CLIENT_IDENTITY,
        "eligibility cohort",
    )
    _require_equal(first.source_row_checksum, second.source_row_checksum, ContractSubject.ROWS, "source-row identities")
    _require_equal(first.score_order_checksum, second.score_order_checksum, ContractSubject.SCORES, "score ordering")
    _require_auroc_invariance(first.aurocs, second.aurocs, auroc_absolute_tolerance)


def _require_equal(left: object, right: object, subject: ContractSubject, name: str) -> None:
    if left != right:
        raise ScientificContractError(f"fixed-score control failed: {name} differs", subject=subject)


def _require_auroc_invariance(
    first: tuple[ClientAurocEvidence, ...], second: tuple[ClientAurocEvidence, ...], tolerance: AbsoluteTolerance
) -> None:
    if tuple(item.client for item in first) != tuple(item.client for item in second):
        raise ScientificContractError(
            "fixed-score control failed: AUROC clients differ", subject=ContractSubject.CLIENT_IDENTITY
        )
    for left, right in zip(first, second, strict=True):
        if left.outcome.status is not right.outcome.status:
            raise ScientificContractError(
                "fixed-score control failed: AUROC availability differs", subject=ContractSubject.HELD_OUT_METRICS
            )
        if left.outcome.status is not MetricStatus.AVAILABLE:
            if left.outcome != right.outcome:
                raise ScientificContractError(
                    "fixed-score control failed: AUROC unavailable outcome differs",
                    subject=ContractSubject.HELD_OUT_METRICS,
                )
            continue
        if left.outcome.value is None or right.outcome.value is None:
            raise RuntimeError("available AUROC evidence must contain values")
        if not floats_absolutely_close(left.outcome.value.value, right.outcome.value.value, tolerance.value):
            raise ScientificContractError(
                "fixed-score control failed: AUROC differs", subject=ContractSubject.HELD_OUT_METRICS
            )
