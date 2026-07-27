"""Distribution-mechanism and locked-client distribution analyses."""

from __future__ import annotations

from datp_core.analysis.contracts import (
    ClientDistributionEntry,
    ClientTradeoffEntry,
    DistributionMechanismAnalysisResult,
    DistributionMechanismRawResult,
    DistributionMechanismSeedResult,
    DistributionMechanismTradeoffResult,
    DistributionMechanismTradeoffSeedResult,
    EvaluationDistributionResult,
    FieldFormulaContract,
    LockedClientDistributionAnalysisResult,
    PairedAnalysisCell,
)
from datp_core.analysis.enums import ProducedField
from datp_core.analysis.errors import ScientificContractViolationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import (
    client_score_distributions,
    threshold_tradeoff,
)
from datp_core.experiments import (
    DistributionMechanismAnalysisRecord,
    LockedClientDistributionAnalysisRecord,
)


def distribution_seed_result(
    context: AnalysisExecutionContext,
    seed: Seed,
    evaluations: tuple[EvaluationLabel, ...],
    client_id: ClientId | None,
) -> DistributionMechanismSeedResult:
    """Extract score distributions across evaluations for one seed."""
    eval_results: list[EvaluationDistributionResult] = []
    for label in evaluations:
        eval_ctx = context.evaluation_context(label, seed)
        score_ctx = context.score_context(label, seed)

        threshold_frame = context.artifacts.thresholds(eval_ctx)
        metric_frame = context.artifacts.client_metrics(eval_ctx)
        score_frame = context.artifacts.test_scores(score_ctx)

        dist_dict = client_score_distributions(
            threshold_frame, metric_frame, score_frame, client_id.value if client_id is not None else None
        )
        entries = tuple(
            ClientDistributionEntry(client_id=ClientId(cid), distribution=dist) for cid, dist in dist_dict.items()
        )
        eval_results.append(EvaluationDistributionResult(evaluation_label=label, clients=entries))

    return DistributionMechanismSeedResult(seed=seed, evaluations=tuple(eval_results))


@run_analysis.register
def analyze_distribution_mechanism(
    specification: DistributionMechanismAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[DistributionMechanismAnalysisResult, ...]:
    """Execute distribution-mechanism analysis across seeds."""
    evals = tuple(EvaluationLabel(label) for label in specification.source_evaluations)
    produced_fields = tuple(ProducedField(field) for field in specification.produced_fields)

    seed_results = tuple(distribution_seed_result(context, seed, evals, None) for seed in context.seeds)

    if specification.field_formulas is None:
        raw_res = DistributionMechanismRawResult(
            analysis_label=AnalysisLabel(specification.label),
            produced_fields=produced_fields,
            seed_results=seed_results,
        )
        return (raw_res,)

    if len(evals) < 2:
        raise ScientificContractViolationError(
            f"Distribution analysis '{specification.label}' needs two source evaluations"
        )

    field_formulas = tuple(
        FieldFormulaContract(field=ProducedField(k), formula=specification.field_formulas[k])
        for k in specification.field_formulas
    )

    tradeoff_seeds: list[DistributionMechanismTradeoffSeedResult] = []
    for res in seed_results:
        baseline_dist = {entry.client_id: entry.distribution for entry in res.evaluations[0].clients}
        shifted_dist = {entry.client_id: entry.distribution for entry in res.evaluations[1].clients}
        tradeoff_map = threshold_tradeoff(
            {cid.value: dist for cid, dist in baseline_dist.items()},
            {cid.value: dist for cid, dist in shifted_dist.items()},
        )
        entries = tuple(
            ClientTradeoffEntry(client_id=ClientId(cid), tradeoff=tradeoff) for cid, tradeoff in tradeoff_map.items()
        )
        tradeoff_seeds.append(DistributionMechanismTradeoffSeedResult(seed=res.seed, per_client_tradeoff=entries))

    tradeoff_res = DistributionMechanismTradeoffResult(
        analysis_label=AnalysisLabel(specification.label),
        field_formulas=field_formulas,
        produced_fields=produced_fields,
        seed_results=tuple(tradeoff_seeds),
    )
    return (tradeoff_res,)


@run_analysis.register
def analyze_locked_client_distribution(
    specification: LockedClientDistributionAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[LockedClientDistributionAnalysisResult, ...]:
    """Execute locked-client distribution analysis across seeds."""
    evals = tuple(EvaluationLabel(label) for label in specification.source_evaluations)
    locked_client = ClientId(specification.locked_client_identifier)
    produced_fields = tuple(ProducedField(field) for field in specification.produced_fields)

    seed_results = tuple(distribution_seed_result(context, seed, evals, locked_client) for seed in context.seeds)
    res = LockedClientDistributionAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        locked_client_identifier=locked_client,
        produced_fields=produced_fields,
        seed_results=seed_results,
    )
    return (res,)
