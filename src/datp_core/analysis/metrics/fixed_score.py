"""Immutable fixed-score evidence contracts for threshold-policy comparisons."""

from dataclasses import dataclass

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.models import MetricAvailability
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId, PartitionRole, StableRowId
from datp_core.core.numeric import ScoreValue
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.training.contracts import FederatedTrainingCoordinate

_CALIBRATION_ROLES = frozenset((PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION))


@dataclass(frozen=True, slots=True)
class FederatedEvaluationScoreArrays:
    """Typed score evidence loaded from one federated evaluation artifact."""

    scores: tuple[ScoreValue, ...]
    labels: tuple[PopulationOutcomeLabel, ...]
    row_ids: tuple[StableRowId, ...]

    def __post_init__(self) -> None:
        if len(self.scores) != len(self.labels) or len(self.scores) != len(self.row_ids):
            raise ValueError("federated evaluation score arrays must have equal lengths")


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
