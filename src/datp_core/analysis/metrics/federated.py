from dataclasses import dataclass, field

from pydantic import ConfigDict

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.conformal import ConformalCoverageDiagnostic
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.analysis.metrics.models import ClientMetricResult, HeldOutBenignScore, PopulationMetricResult
from datp_core.analysis.metrics.threshold_estimation import (
    SampleEfficiencyPoint,
    ThresholdEstimationDiagnostic,
    ThresholdEstimationProvenance,
)
from datp_core.analysis.metrics.threshold_evidence import VerifiedHeldOutBenignScores
from datp_core.analysis.operational.alert_burden import AlertBurdenDiagnostic
from datp_core.analysis.operational.communication import CommunicationDiagnostic, CommunicationMessageDiagnostic
from datp_core.analysis.operational.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import CoordinateStableKey, EvidenceRole, FederatedThresholdMethod, StageOperationId
from datp_core.core.numeric import (
    CalibrationSize,
    CoverageTarget,
    ReplicateIndex,
    ShrinkageWeight,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.thresholds.dispatch import ThresholdConstructionResult
from datp_core.thresholds.variants.conformal import ConformalAssignment

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


@dataclass(frozen=True, slots=True)
class ShrinkageLambdaEvaluation:
    lambda_weight: ShrinkageWeight
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult

    def __post_init__(self) -> None:
        if not self.clients:
            raise ScientificContractError(ErrorMessage("shrinkage lambda evaluation requires client metrics"))
        if len({item.client for item in self.clients}) != len(self.clients):
            raise ScientificContractError(ErrorMessage("shrinkage lambda evaluation cannot repeat clients"))


@dataclass(frozen=True, slots=True)
class CalibrationSizeAblationCell:
    calibration_size: CalibrationSize
    replicate_index: ReplicateIndex
    method: FederatedThresholdMethod
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult

    def __post_init__(self) -> None:
        if not self.clients:
            raise ScientificContractError(ErrorMessage("calibration-size ablation cell requires client metrics"))
        if len({item.client for item in self.clients}) != len(self.clients):
            raise ScientificContractError(ErrorMessage("calibration-size ablation cannot repeat clients"))


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
            raise ScientificContractError(ErrorMessage("threshold-estimation evidence must match the evaluated client"))
        if self.verified_benign_scores.coordinate != self.provenance.coordinate:
            raise ScientificContractError(
                ErrorMessage("threshold-estimation evidence must match the evaluated coordinate")
            )


@dataclass(frozen=True, slots=True)
class EvaluationDiagnostics:
    conformal_coverage: tuple[ConformalCoverageDiagnostic, ...]
    threshold_estimation: tuple[ThresholdEstimationDiagnostic, ...]
    communication: CommunicationDiagnostic | None
    alert_burden: tuple[AlertBurdenDiagnostic, ...]
    shrinkage_curve: tuple[ShrinkageLambdaEvaluation, ...] = field(default_factory=tuple)
    calibration_size_ablation: tuple[CalibrationSizeAblationCell, ...] = field(default_factory=tuple)
    sample_efficiency: tuple[SampleEfficiencyPoint, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FederatedEvaluationRequest:
    execution_key: CoordinateStableKey
    score_manifest: FederatedScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    evidence_role: EvidenceRole
    conformal_coverage_inputs: tuple[ConformalCoverageStageInput, ...]
    threshold_estimation_inputs: tuple[ThresholdEstimationStageInput, ...]
    communication_messages: tuple[CommunicationMessageDiagnostic, ...]
    traffic_rate_evidence: ValidatedTrafficRateEvidence | None
    temporal_provenance: TemporalDeploymentProvenance | None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None
    execution_identity: ExternalTemporalExecutionIdentity | None
    calibration_size_ablation: tuple[CalibrationSizeAblationCell, ...] = ()


class FederatedEvaluationDocument(StrictModel):
    model_config = ConfigDict(revalidate_instances="never")
    stage: StageOperationId
    execution_key: CoordinateStableKey
    score_coordinate: FederatedTrainingCoordinate
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
