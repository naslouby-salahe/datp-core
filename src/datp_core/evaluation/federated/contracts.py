"""Contracts for held-out federated evaluation and its diagnostics."""

from dataclasses import dataclass

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, FederatedThresholdMethod, StageOperationId
from datp_core.domain.values import Checksum, CoverageTarget, ThresholdValue
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.communication import CommunicationDiagnostic, CommunicationMessageDiagnostic
from datp_core.evaluation.conformal_coverage import ConformalCoverageDiagnostic
from datp_core.evaluation.fixed_score.contracts import FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, HeldOutBenignScore, PopulationMetricResult
from datp_core.evaluation.operational import AlertBurdenDiagnostic
from datp_core.evaluation.threshold_estimation import ThresholdEstimationDiagnostic, ThresholdEstimationProvenance
from datp_core.evaluation.threshold_evidence import VerifiedHeldOutBenignScores
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.inference import ScoreArtifactManifest
from datp_core.protocols.temporal import TemporalDeploymentProvenance
from datp_core.thresholding.methods.conformal import ConformalAssignment
from datp_core.thresholding.models import ThresholdConstructionResult


@dataclass(frozen=True, slots=True)
class ConformalCoverageStageInput:
    assignment: ConformalAssignment
    target_coverage: CoverageTarget
    held_out_benign_scores: tuple[HeldOutBenignScore, ...]


@dataclass(frozen=True, slots=True)
class ThresholdEstimationStageInput:
    provenance: ThresholdEstimationProvenance
    estimated_threshold: ThresholdValue
    exact_pooled_benign_quantile_reference: ThresholdValue
    verified_benign_scores: VerifiedHeldOutBenignScores

    def __post_init__(self) -> None:
        if self.verified_benign_scores.client != self.provenance.client:
            raise ValueError("threshold-estimation evidence must match the evaluated client")
        if self.verified_benign_scores.coordinate != self.provenance.coordinate:
            raise ValueError("threshold-estimation evidence must match the evaluated coordinate")


@dataclass(frozen=True, slots=True)
class EvaluationDiagnostics:
    conformal_coverage: tuple[ConformalCoverageDiagnostic, ...]
    threshold_estimation: tuple[ThresholdEstimationDiagnostic, ...]
    communication: CommunicationDiagnostic | None
    alert_burden: tuple[AlertBurdenDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class FederatedEvaluationRequest:
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
    temporal_provenance: TemporalDeploymentProvenance | None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None
    execution_identity: ExternalTemporalExecutionIdentity | None


class FederatedEvaluationDocument(StrictModel):
    stage: StageOperationId
    score_coordinate: FederatedTrainingCoordinate
    score_checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    threshold_method: FederatedThresholdMethod
    evidence_role: EvidenceRole
    fixed_score_evidence: FixedScoreEvidence
    cohort: EvaluationCohortManifest
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    temporal_provenance: TemporalDeploymentProvenance | None


@dataclass(frozen=True, slots=True)
class FederatedEvaluationArtifacts:
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics


@dataclass(frozen=True, slots=True)
class FederatedEvaluationPublication:
    artifacts: FederatedEvaluationArtifacts
    document: FederatedEvaluationDocument
    digest: Checksum
