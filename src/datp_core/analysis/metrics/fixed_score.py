from dataclasses import dataclass

import numpy as np

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
    score_values: np.ndarray
    attack_mask: np.ndarray

    def __post_init__(self) -> None:
        if len(self.scores) != len(self.labels) or len(self.scores) != len(self.row_ids):
            raise ValueError("federated evaluation score arrays must have equal lengths")
        if self.score_values.ndim != 1 or self.attack_mask.ndim != 1:
            raise ValueError("federated evaluation score arrays must be one dimensional")
        if len(self.scores) != self.score_values.size or len(self.scores) != self.attack_mask.size:
            raise ValueError("federated evaluation numeric arrays must align with semantic arrays")


@dataclass(frozen=True, slots=True)
class FixedScoreEvidence:
    threshold_method: FederatedThresholdMethod
    calibration_role: PartitionRole
    score_manifest: FederatedScoreArtifactManifest


@dataclass(frozen=True, slots=True)
class FederatedEvaluationInputs:
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
