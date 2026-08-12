from dataclasses import dataclass, field

from pydantic import ConfigDict

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.conformal import ConformalCoverageDiagnostic
from datp_core.analysis.metrics.family_recall import FamilyRecallDiagnostics
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.analysis.metrics.models import ClientMetricResult, HeldOutBenignScore, PopulationMetricResult
from datp_core.analysis.metrics.operating_point import (
    CalibrationSupportEvidence,
    HeldOutOperatingPointDiagnostic,
    HeldOutOperatingPointSummary,
)
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
    OnboardingCalibrationSize,
    Quantile,
    ReplicateIndex,
    ShrinkageWeight,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.thresholds.contracts import ThresholdInfeasibilityReason
from datp_core.thresholds.dispatch import ThresholdConstructionResult
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores
from datp_core.thresholds.variants.conformal import ConformalAssignment

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


@dataclass(frozen=True, slots=True)
class ShrinkageLambdaEvaluation:
    lambda_weight: ShrinkageWeight
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    held_out_operating_points: tuple[HeldOutOperatingPointDiagnostic, ...]
    held_out_operating_point_summary: HeldOutOperatingPointSummary | None

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
    held_out_operating_points: tuple[HeldOutOperatingPointDiagnostic, ...]
    held_out_operating_point_summary: HeldOutOperatingPointSummary | None

    def __post_init__(self) -> None:
        if not self.clients:
            raise ScientificContractError(ErrorMessage("calibration-size ablation cell requires client metrics"))
        if len({item.client for item in self.clients}) != len(self.clients):
            raise ScientificContractError(ErrorMessage("calibration-size ablation cannot repeat clients"))


@dataclass(frozen=True, slots=True)
class OnboardingCalibrationCell:
    target_client: ClientIdentity
    calibration_size: OnboardingCalibrationSize
    replicate_index: ReplicateIndex
    method: FederatedThresholdMethod
    target_metrics: ClientMetricResult | None
    target_threshold: ThresholdValue | None
    full_calibration_local_threshold: ThresholdValue
    unavailable_reason: ThresholdInfeasibilityReason | None
    family_fallback: bool = False

    def __post_init__(self) -> None:
        if self.target_metrics is not None and self.target_metrics.client != self.target_client:
            raise ScientificContractError(ErrorMessage("onboarding target metrics must belong to the target client"))
        if (self.target_metrics is None) != (self.target_threshold is None):
            raise ScientificContractError(
                ErrorMessage("onboarding target metrics and threshold must be available together")
            )
        if self.target_metrics is not None and self.unavailable_reason is not None:
            raise ScientificContractError(
                ErrorMessage("available onboarding target cannot carry an unavailable reason")
            )
        if self.target_metrics is None and self.unavailable_reason is None:
            raise ScientificContractError(ErrorMessage("unavailable onboarding target requires a typed reason"))


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
    held_out_operating_points: tuple[HeldOutOperatingPointDiagnostic, ...]
    held_out_operating_point_summary: HeldOutOperatingPointSummary | None
    calibration_support: tuple[CalibrationSupportEvidence, ...]
    family_recall: FamilyRecallDiagnostics
    shrinkage_curve: tuple[ShrinkageLambdaEvaluation, ...] = field(default_factory=tuple)
    calibration_size_ablation: tuple[CalibrationSizeAblationCell, ...] = field(default_factory=tuple)
    onboarding_calibration: tuple[OnboardingCalibrationCell, ...] = field(default_factory=tuple)
    sample_efficiency: tuple[SampleEfficiencyPoint, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FederatedEvaluationRequest:
    execution_key: CoordinateStableKey
    score_manifest: FederatedScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    evidence_role: EvidenceRole
    calibration_scores: tuple[ClientBenignCalibrationScores, ...]
    target_quantile: Quantile
    conformal_coverage_inputs: tuple[ConformalCoverageStageInput, ...]
    threshold_estimation_inputs: tuple[ThresholdEstimationStageInput, ...]
    communication_messages: tuple[CommunicationMessageDiagnostic, ...]
    traffic_rate_evidence: ValidatedTrafficRateEvidence | None
    temporal_provenance: TemporalDeploymentProvenance | None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None
    execution_identity: ExternalTemporalExecutionIdentity | None
    calibration_size_ablation: tuple[CalibrationSizeAblationCell, ...] = ()
    onboarding_calibration: tuple[OnboardingCalibrationCell, ...] = ()


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
