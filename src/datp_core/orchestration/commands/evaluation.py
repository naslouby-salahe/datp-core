"""Typed evaluation commands and stage outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.centralized_reference.evaluation import CentralizedEvaluationResult
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import EvidenceRole, PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum
from datp_core.evaluation.cohorts import EvaluationCohortManifest
from datp_core.evaluation.communication import CommunicationMessageDiagnostic
from datp_core.evaluation.controls import FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, PopulationMetricResult
from datp_core.evaluation.population import (
    ConformalCoverageStageInput,
    EvaluationDiagnostics,
    ThresholdEstimationStageInput,
)
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.models import ThresholdConstructionResult


@dataclass(frozen=True, slots=True)
class EvaluateCentralizedReferenceRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class EvaluateCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.EVALUATE_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    evaluation: CentralizedEvaluationResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class EvaluateFederatedRequest:
    score_manifest: ScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    comparison_fixed_score_evidence: FixedScoreEvidence | None
    evidence_role: EvidenceRole
    conformal_coverage_inputs: tuple[ConformalCoverageStageInput, ...]
    threshold_estimation_inputs: tuple[ThresholdEstimationStageInput, ...]
    communication_messages: tuple[CommunicationMessageDiagnostic, ...]
    traffic_rate_evidence: ValidatedTrafficRateEvidence | None
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None = None
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(frozen=True, slots=True)
class FederatedEvaluationResult:
    stage: ClassVar[StageOperationId] = StageOperationId.EVALUATE_FEDERATED
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum
