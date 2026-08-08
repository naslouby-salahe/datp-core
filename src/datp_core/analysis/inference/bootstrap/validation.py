"""Scientific design validation for paired bootstrap inference."""

from datp_core.analysis.contrasts import FixedScorePairProvenance, PairedContrasts, SupplementaryPairedAnalysisPlan
from datp_core.analysis.inference.bootstrap.contracts import BcaReason
from datp_core.analysis.inference.wilcoxon import PairedInferenceProtocol
from datp_core.core.identifiers import EvidenceRole, FederatedThresholdMethod
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH


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
    observed_seeds = {contrast.seed for contrast in contrasts}
    if len(observed_seeds) != len(contrasts):
        raise PairedAnalysisContractError(BcaReason.DUPLICATE_SEED)
    if observed_seeds != set(endpoint.seed_cohort.values):
        raise PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    for contrast in contrasts:
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
    return tuple(sorted(contrasts, key=lambda contrast: contrast.seed.value))


def validate_supplementary_contrasts(
    contrasts: PairedContrasts,
    plan: SupplementaryPairedAnalysisPlan,
) -> PairedContrasts:
    observed_seeds = {contrast.seed for contrast in contrasts}
    if len(observed_seeds) != len(contrasts):
        raise PairedAnalysisContractError(BcaReason.DUPLICATE_SEED)
    if observed_seeds != set(plan.seed_cohort.values):
        raise PairedAnalysisContractError(BcaReason.SUPPLEMENTARY_SEED_COHORT_MISMATCH)
    for contrast in contrasts:
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
    return tuple(sorted(contrasts, key=lambda contrast: contrast.seed.value))


def _require_fixed_design(contrasts: PairedContrasts) -> None:
    if not contrasts:
        raise PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    design = contrasts[0].design
    if any(contrast.design != design for contrast in contrasts[1:]):
        raise PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _require_fixed_score_identity(contrasts: PairedContrasts) -> None:
    """Reject pairs that only share a training coordinate without fixed-score provenance."""
    if not contrasts:
        raise PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    for contrast in contrasts:
        _require_complete_provenance(contrast.fixed_score)
    methods = (contrasts[0].left_method, contrasts[0].right_method)
    if any((contrast.left_method, contrast.right_method) != methods for contrast in contrasts[1:]):
        raise PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _require_complete_provenance(provenance: FixedScorePairProvenance) -> None:
    fields = (
        provenance.model_checksum,
        provenance.preprocessing_checksum,
        provenance.selected_checkpoint_checksum,
        provenance.split_manifest_checksum,
        provenance.calibration_score_checksum,
        provenance.evaluation_score_checksum,
        provenance.evaluation_label_checksum,
        provenance.source_row_checksum,
        provenance.score_order_checksum,
        provenance.client_inventory_checksum,
        provenance.eligibility_cohort_checksum,
    )
    if any(not field.value for field in fields):
        raise PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)
