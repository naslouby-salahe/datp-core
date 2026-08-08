"""Confirmatory endpoint validation and claim decision."""

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import paired_bca_interval
from datp_core.analysis.inference.contrasts import PairedContrasts
from datp_core.analysis.inference.decisions import ScientificDecision, ScientificDecisionResult, blocked_decision
from datp_core.analysis.inference.wilcoxon import (
    RankBiserialResult,
    WilcoxonResult,
    matched_pairs_rank_biserial,
    paired_wilcoxon,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole
from datp_core.core.numeric import MetricValue
from datp_core.experiments.confirmatory.spec import (
    CONFIRMATORY_BOOTSTRAP_SEED,
    CONFIRMATORY_ENDPOINT,
)


class ConfirmatoryAnalysis(StrictModel):
    interval: BootstrapInterval
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    decision: ScientificDecisionResult


def analyze_confirmatory(contrasts: PairedContrasts) -> ConfirmatoryAnalysis:
    mismatch = _confirmatory_mismatch(contrasts)
    if mismatch is not None:
        interval = paired_bca_interval(
            (),
            protocol=CONFIRMATORY_ENDPOINT.inference_protocol,
            analysis_seed=CONFIRMATORY_BOOTSTRAP_SEED,
        )
        decision = blocked_decision(evidence_role=EvidenceRole.CONFIRMATORY, rationale=mismatch, interval=interval)
        return ConfirmatoryAnalysis(
            interval=interval,
            wilcoxon=paired_wilcoxon((), CONFIRMATORY_ENDPOINT.inference_protocol),
            rank_biserial=matched_pairs_rank_biserial((), CONFIRMATORY_ENDPOINT.inference_protocol),
            decision=decision,
        )

    interval = paired_bca_interval(
        contrasts,
        protocol=CONFIRMATORY_ENDPOINT.inference_protocol,
        analysis_seed=CONFIRMATORY_BOOTSTRAP_SEED,
    )
    wilcoxon = paired_wilcoxon(contrasts, CONFIRMATORY_ENDPOINT.inference_protocol)
    rank_biserial = matched_pairs_rank_biserial(contrasts, CONFIRMATORY_ENDPOINT.inference_protocol)
    return ConfirmatoryAnalysis(
        interval=interval,
        wilcoxon=wilcoxon,
        rank_biserial=rank_biserial,
        decision=_confirmatory_decision(interval),
    )


def _confirmatory_mismatch(contrasts: PairedContrasts) -> str | None:
    endpoint = CONFIRMATORY_ENDPOINT
    if len(contrasts) != endpoint.seed_cohort.member_count.value:
        return "confirmatory evidence must contain the complete ten-seed paired cohort"
    observed_seeds = tuple(contrast.seed for contrast in contrasts)
    if len(frozenset(observed_seeds)) != len(observed_seeds):
        return "confirmatory evidence must be unique by training seed"
    if frozenset(observed_seeds) != frozenset(endpoint.seed_cohort.values):
        return "confirmatory evidence must equal the declared seed cohort"
    for contrast in contrasts:
        coordinate = contrast.coordinate
        if (
            contrast.evidence_role is not EvidenceRole.CONFIRMATORY
            or coordinate.population is not endpoint.population
            or coordinate.model is not endpoint.training_model
            or coordinate.preprocessing_identity is not endpoint.preprocessing_protocol
            or contrast.metric is not endpoint.metric
            or contrast.left_method is not endpoint.shared_threshold
            or contrast.right_method is not endpoint.local_threshold
        ):
            return "confirmatory evidence does not match the declared fixed endpoint"
    return None


def _confirmatory_decision(interval: BootstrapInterval) -> ScientificDecisionResult:
    if (
        interval.availability is not AvailabilityStatus.AVAILABLE
        or interval.point_estimate is None
        or interval.lower_bound is None
        or interval.upper_bound is None
    ):
        return blocked_decision(
            evidence_role=EvidenceRole.CONFIRMATORY,
            rationale="confirmatory BCa interval is unavailable or degenerate",
            interval=interval,
        )
    if interval.lower_bound.value > 0.0:
        decision = ScientificDecision.SUPPORTED
        rationale = "the paired BCa interval supports lower CV(FPR) under local thresholds"
    elif interval.upper_bound.value < 0.0:
        decision = ScientificDecision.OPPOSITE_DIRECTION
        rationale = "the paired BCa interval supports the opposite direction"
    elif interval.point_estimate.value > 0.0:
        decision = ScientificDecision.DIRECTIONAL_INCONCLUSIVE
        rationale = "the point estimate is directional but the paired BCa interval crosses zero"
    else:
        decision = ScientificDecision.NO_OBSERVED_ADVANTAGE
        rationale = "the paired BCa interval crosses zero without a positive point estimate"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.CONFIRMATORY,
        decision=decision,
        point_estimate=MetricValue(interval.point_estimate.value),
        interval=interval,
        rationale=rationale,
    )
