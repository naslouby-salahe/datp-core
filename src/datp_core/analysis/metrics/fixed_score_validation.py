from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.analysis.metrics.models import ClientMetricResult
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ContractSubject
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest


def validate_evaluation_evidence(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    del cohort, clients
    if evidence.score_manifest != manifest:
        raise ScientificContractError(
            ErrorMessage("evaluation must consume the score evidence created for this execution"),
            subject=ContractSubject.SCORES,
        )


def validate_fixed_score_controls(first: FixedScoreEvidence, second: FixedScoreEvidence) -> None:
    if first.threshold_method is second.threshold_method:
        raise ScientificContractError(ErrorMessage("fixed-score comparison requires distinct threshold methods"))
    if first.calibration_role is not second.calibration_role:
        raise ScientificContractError(ErrorMessage("fixed-score control failed: calibration partition role differs"))
    if first.score_manifest != second.score_manifest:
        raise ScientificContractError(ErrorMessage("fixed-score comparison requires the same score evidence"))
