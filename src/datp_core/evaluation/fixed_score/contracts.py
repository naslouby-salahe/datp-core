"""Immutable fixed-score evidence contracts for threshold-policy comparisons."""

from dataclasses import dataclass

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import FederatedThresholdMethod, MetricId, PartitionRole
from datp_core.domain.values import Checksum
from datp_core.evaluation.cohorts import EvaluationCohortManifest
from datp_core.evaluation.models import MetricAvailability
from datp_core.learning.federated.models import FederatedTrainingCoordinate

_CALIBRATION_ROLES = frozenset((PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION))


@dataclass(frozen=True, slots=True)
class ClientAurocEvidence:
    client: ClientIdentity
    outcome: MetricAvailability

    def __post_init__(self) -> None:
        if self.outcome.metric is not MetricId.AUROC:
            raise ValueError("AUROC evidence must carry the AUROC metric")


@dataclass(frozen=True, slots=True)
class DetectorEvidence:
    coordinate: FederatedTrainingCoordinate
    model_checksum: Checksum
    preprocessing_checksum: Checksum
    selected_checkpoint_checksum: Checksum


@dataclass(frozen=True, slots=True)
class CalibrationEvidence:
    role: PartitionRole
    score_checksum: Checksum

    def __post_init__(self) -> None:
        if self.role not in _CALIBRATION_ROLES:
            raise ValueError("fixed-score evidence requires a calibration partition role")


@dataclass(frozen=True, slots=True)
class HeldOutEvaluationEvidence:
    score_checksum: Checksum
    label_checksum: Checksum
    source_row_checksum: Checksum
    score_order_checksum: Checksum
    aurocs: tuple[ClientAurocEvidence, ...]

    def __post_init__(self) -> None:
        clients = tuple(item.client for item in self.aurocs)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("AUROC evidence must be unique by client")


@dataclass(frozen=True, slots=True)
class PopulationEvidence:
    client_inventory_checksum: Checksum
    eligibility_cohort_checksum: Checksum


@dataclass(frozen=True, slots=True)
class FixedScoreEvidence:
    """Evidence that must remain invariant while only threshold policy changes."""

    threshold_method: FederatedThresholdMethod
    detector: DetectorEvidence
    calibration: CalibrationEvidence
    evaluation: HeldOutEvaluationEvidence
    population: PopulationEvidence


@dataclass(frozen=True, slots=True)
class FederatedEvaluationInputs:
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
