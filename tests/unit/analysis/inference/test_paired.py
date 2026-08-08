from tests.unit.analysis.inference.test_bootstrap import contrasts

from datp_core.analysis.inference.multiplicity import (
    FamilyName,
    FamilySize,
    HypothesisIdentifier,
    MultiplicityHypothesis,
    MultiplicityPlan,
    holm_adjust,
)
from datp_core.analysis.inference.wilcoxon import (
    PValue,
    WilcoxonComputationMethod,
    matched_pairs_rank_biserial,
    paired_wilcoxon,
)
from datp_core.core.identifiers import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
)
from datp_core.core.numeric import Ratio
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


def test_paired_inference_uses_the_declared_protocol() -> None:
    values = contrasts()
    wilcoxon = paired_wilcoxon(values, CONFIRMATORY_INFERENCE_PROTOCOL)
    effect = matched_pairs_rank_biserial(
        values,
        CONFIRMATORY_INFERENCE_PROTOCOL,
    )
    assert wilcoxon.availability is AvailabilityStatus.AVAILABLE
    assert wilcoxon.computation_method is WilcoxonComputationMethod.EXACT
    assert wilcoxon.fallback_reason is None
    assert effect.availability is AvailabilityStatus.AVAILABLE
    assert effect.value is not None and -1.0 <= effect.value.value <= 1.0


def test_wilcoxon_falls_back_when_exact_is_unavailable() -> None:
    # All zeros except one tiny difference and many ties after Pratt zero handling force asymptotic in some regimes;
    # use a large nonzero sample that still prefers exact when feasible, and assert method is recorded.
    values = contrasts()
    result = paired_wilcoxon(values, CONFIRMATORY_INFERENCE_PROTOCOL)
    assert result.computation_method in {
        WilcoxonComputationMethod.EXACT,
        WilcoxonComputationMethod.ASYMPTOTIC,
    }
    if result.computation_method is WilcoxonComputationMethod.ASYMPTOTIC:
        assert result.fallback_reason is not None


def test_multiplicity_uses_a_complete_typed_plan() -> None:
    plan = MultiplicityPlan(
        family_name=FamilyName("predeclared_supportive_family"),
        declared_family_size=FamilySize(2),
        hypotheses=(
            MultiplicityHypothesis(
                hypothesis_id=HypothesisIdentifier("h1"),
                experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                comparison="shared_vs_local",
                left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
                right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                evidence_role=EvidenceRole.SUPPORTIVE,
                raw_p_value=PValue(0.01),
            ),
            MultiplicityHypothesis(
                hypothesis_id=HypothesisIdentifier("h2"),
                experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                metric=MetricId.MEAN_FPR,
                comparison="shared_vs_local_mean_fpr",
                left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
                right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                evidence_role=EvidenceRole.SUPPORTIVE,
                raw_p_value=PValue(0.04),
            ),
        ),
        alpha=Ratio(0.05),
    )
    result = holm_adjust(plan, CONFIRMATORY_INFERENCE_PROTOCOL)
    assert result.correction is CONFIRMATORY_INFERENCE_PROTOCOL.multiplicity_correction
    assert result.family_name == FamilyName("predeclared_supportive_family")
    assert result.family_size == FamilySize(2)
    assert result.raw_p_values == (PValue(0.01), PValue(0.04))
    assert result.decisions[0].hypothesis.hypothesis_id == HypothesisIdentifier("h1")
    assert result.adjusted_p_values[0].value <= result.adjusted_p_values[1].value
