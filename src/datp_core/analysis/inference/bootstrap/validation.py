from datp_core.analysis.contrasts import PairedContrasts, SupplementaryPairedAnalysisPlan
from datp_core.analysis.inference.bootstrap.contracts import BcaReason
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.core.identifiers import EvidenceRole, FederatedThresholdMethod
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.graph import CANONICAL_PROTOCOL_GRAPH


class PairedAnalysisContractError(ValueError):
    def __init__(self, reason: BcaReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


def validate_confirmatory_contrasts(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
) -> PairedContrasts:
    canonical = CANONICAL_PROTOCOL_GRAPH
    if protocol != canonical.confirmatory_inference:
        raise PairedAnalysisContractError(BcaReason.CANONICAL_PROTOCOL_MISMATCH)
    endpoint = canonical.confirmatory_endpoint
    _require_complete_seed_cohort(
        contrasts,
        endpoint.seed_cohort,
        BcaReason.SEED_COHORT_MISMATCH,
    )
    for contrast in contrasts.values:
        if (
            contrast.evidence_role is not EvidenceRole.CONFIRMATORY
            or contrast.coordinate.population is not endpoint.population
            or contrast.coordinate.model is not endpoint.training_model
            or contrast.metric is not endpoint.metric
            or contrast.left_method is not endpoint.shared_threshold
            or contrast.right_method is not endpoint.local_threshold
            or contrast.left_method is not FederatedThresholdMethod.SHARED_THRESHOLD
            or contrast.right_method is not FederatedThresholdMethod.LOCAL_THRESHOLD
        ):
            raise PairedAnalysisContractError(BcaReason.CONFIRMATORY_ENDPOINT_MISMATCH)
    _require_fixed_design(contrasts)
    _require_fixed_score_identity(contrasts)
    return contrasts.ordered_by_seed()


def validate_supplementary_contrasts(
    contrasts: PairedContrasts,
    plan: SupplementaryPairedAnalysisPlan,
) -> PairedContrasts:
    _require_complete_seed_cohort(
        contrasts,
        plan.seed_cohort,
        BcaReason.SUPPLEMENTARY_SEED_COHORT_MISMATCH,
    )
    for contrast in contrasts.values:
        if (
            contrast.coordinate.population is not plan.population
            or contrast.evidence_role is not plan.evidence_role
            or contrast.metric is not plan.metric
            or contrast.left_method is not plan.left_method
            or contrast.right_method is not plan.right_method
        ):
            raise PairedAnalysisContractError(BcaReason.SUPPLEMENTARY_ANALYSIS_PLAN_MISMATCH)
    _require_fixed_design(contrasts)
    _require_fixed_score_identity(contrasts)
    return contrasts.ordered_by_seed()


def _require_complete_seed_cohort(
    contrasts: PairedContrasts,
    declared_cohort: SeedCohort,
    mismatch_reason: BcaReason,
) -> None:
    observed_seeds = frozenset(contrast.seed for contrast in contrasts.values)
    if observed_seeds != frozenset(declared_cohort.values):
        raise PairedAnalysisContractError(mismatch_reason)


def _require_fixed_design(contrasts: PairedContrasts) -> None:
    if not contrasts:
        raise PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    design = contrasts[0].design
    if any(contrast.design != design for contrast in contrasts[1:]):
        raise PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _require_fixed_score_identity(contrasts: PairedContrasts) -> None:

    if not contrasts:
        raise PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    for contrast in contrasts.values:
        _require_complete_provenance(contrast.fixed_score)
    methods = (contrasts[0].left_method, contrasts[0].right_method)
    if any((contrast.left_method, contrast.right_method) != methods for contrast in contrasts[1:]):
        raise PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _require_complete_provenance(provenance: FixedScoreEvidence) -> None:
    if not provenance.score_manifest.calibration_records or not provenance.score_manifest.evaluation_records:
        raise PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)
