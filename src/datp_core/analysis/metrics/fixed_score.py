from dataclasses import dataclass

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.core.identifiers import FederatedThresholdMethod, PartitionRole, StableRowId
from datp_core.core.numeric import ScoreValue
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.models import FederatedTrainingCoordinate

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


@dataclass(frozen=True, slots=True)
class FederatedEvaluationScoreArrays:
    scores: tuple[ScoreValue, ...]
    labels: tuple[PopulationOutcomeLabel, ...]
    row_ids: tuple[StableRowId, ...]

    def __post_init__(self) -> None:
        if len(self.scores) != len(self.labels) or len(self.scores) != len(self.row_ids):
            raise ValueError("federated evaluation score arrays must have equal lengths")


@dataclass(frozen=True, slots=True)
class FixedScoreEvidence:
    threshold_method: FederatedThresholdMethod
    calibration_role: PartitionRole
    score_manifest: FederatedScoreArtifactManifest


@dataclass(frozen=True, slots=True)
class FederatedEvaluationInputs:
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
