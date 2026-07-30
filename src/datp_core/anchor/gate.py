"""Gate decision for historical anchor reproduction and dependent-experiment readiness."""

from pathlib import Path

from datp_core.anchor.models import (
    DECLARED_NON_BLOCKING_DISCREPANCY_REASONS,
    AnchorArtifactFileName,
    AnchorComparisonDecision,
    AnchorDependencyBlocker,
    AnchorDiscrepancy,
    AnchorGateDecision,
    AnchorGateStatus,
    AnchorMetricComparison,
    AnchorReproductionResult,
    AnchorSeedSubsetComparison,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import ExperimentReadiness
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Checksum, checksum_text
from datp_core.protocols.models import SeedCohort


def decide_anchor_gate(reproduction: AnchorReproductionResult) -> AnchorGateDecision:
    """Derive an irreversible gate decision from a typed reproduction result."""
    blocking, declared = _partition_discrepancies(reproduction.discrepancies)
    mandatory_ok = _all_mandatory_comparisons_equivalent(reproduction)
    if reproduction.dependency_blocker is not None or blocking or not mandatory_ok:
        return AnchorGateDecision(
            status=AnchorGateStatus.BLOCKED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            reproduction=reproduction,
            blocking_discrepancies=blocking if blocking else reproduction.discrepancies,
            declared_discrepancies=(),
        )
    if declared:
        return AnchorGateDecision(
            status=AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
            dependent_readiness=ExperimentReadiness.DECLARED,
            reproduction=reproduction,
            blocking_discrepancies=(),
            declared_discrepancies=declared,
        )
    return AnchorGateDecision(
        status=AnchorGateStatus.PASS,
        dependent_readiness=ExperimentReadiness.DECLARED,
        reproduction=reproduction,
        blocking_discrepancies=(),
        declared_discrepancies=(),
    )


def dependent_readiness_from_gate(decision: AnchorGateDecision) -> ExperimentReadiness:
    """Map gate status to dependent-experiment readiness. No caller override is accepted."""
    if decision.status is AnchorGateStatus.BLOCKED:
        return ExperimentReadiness.BLOCKED
    if decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}:
        return ExperimentReadiness.DECLARED
    raise AnchorReproductionError(
        "unknown anchor gate status",
        subject=decision.status,
    )


def assert_gate_not_bypassable(decision: AnchorGateDecision) -> AnchorGateDecision:
    """Structural guard: blocked gates never expose claim-permitted dependent readiness."""
    if decision.dependent_readiness is ExperimentReadiness.EXECUTABLE:
        raise AnchorReproductionError(
            "anchor gate cannot mark dependent experiments executable",
            subject=decision.dependent_readiness,
        )
    if decision.status is AnchorGateStatus.BLOCKED:
        _assert_blocked_gate_integrity(decision)
    return decision


def _assert_blocked_gate_integrity(decision: AnchorGateDecision) -> None:
    if decision.dependent_readiness is not ExperimentReadiness.BLOCKED:
        raise AnchorReproductionError(
            "blocked anchor gate cannot permit dependent readiness",
            subject=decision.status,
        )
    has_diagnostics = bool(decision.reproduction.discrepancies) or decision.reproduction.dependency_blocker is not None
    if not has_diagnostics:
        raise AnchorReproductionError(
            "blocked anchor gate erased diagnostic state",
            subject=decision.status,
        )


def _all_mandatory_comparisons_equivalent(reproduction: AnchorReproductionResult) -> bool:
    seed_ok = reproduction.seed_subset_comparison.decision is AnchorComparisonDecision.EQUIVALENT
    comparisons = reproduction.metric_comparisons
    metrics_ok = bool(comparisons) and all(
        comparison.decision is AnchorComparisonDecision.EQUIVALENT for comparison in comparisons
    )
    return seed_ok and metrics_ok


def _partition_discrepancies(
    discrepancies: tuple[AnchorDiscrepancy, ...],
) -> tuple[tuple[AnchorDiscrepancy, ...], tuple[AnchorDiscrepancy, ...]]:
    """Split discrepancies into blocking vs declared non-blocking classes."""
    allowed = DECLARED_NON_BLOCKING_DISCREPANCY_REASONS
    if not allowed:
        return discrepancies, ()
    blocking = tuple(item for item in discrepancies if item.reason not in allowed)
    declared = tuple(item for item in discrepancies if item.reason in allowed)
    return blocking, declared


class DependencyBlockerDocument(StrictModel):
    kind: str
    detail: str


class SeedSubsetComparisonDocument(StrictModel):
    expected_seeds: tuple[int, ...]
    observed_seeds: tuple[int, ...]
    decision: str
    reason: str | None


class MetricComparisonDocument(StrictModel):
    seed: int
    threshold_method: str
    metric: str
    expected: float
    observed: float | None
    decision: str
    signed_difference: float | None
    relative_difference: float | None
    tolerance_strategy: str
    reason: str | None


class DiscrepancyDocument(StrictModel):
    reason: str
    seed: int | None
    threshold_method: str | None
    metric: str | None
    expected_value: float | None
    observed_value: float | None
    signed_difference: float | None
    relative_difference: float | None
    tolerance_strategy: str | None
    artifact_path: str | None
    artifact_checksum: str | None
    detail: str


class ReproductionDocument(StrictModel):
    experiment: str
    evidence_role: str
    seed_cohort: tuple[int, ...]
    reference_count: int
    observation_count: int
    seed_subset: SeedSubsetComparisonDocument
    metric_comparisons: tuple[MetricComparisonDocument, ...]
    discrepancies: tuple[DiscrepancyDocument, ...]
    dependency_blocker: DependencyBlockerDocument | None


class GateDecisionDocument(StrictModel):
    status: str
    dependent_readiness: str
    blocking_discrepancies: tuple[DiscrepancyDocument, ...]
    declared_discrepancies: tuple[DiscrepancyDocument, ...]
    reproduction: ReproductionDocument


def persist_anchor_gate_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> Checksum:
    document = gate_decision_document(decision)
    payload = document.model_dump_json()
    checksum = checksum_text(payload)
    if diagnostics_directory is None:
        return checksum
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    (diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value).write_text(payload, encoding="utf-8")
    discrepancies = tuple(discrepancy_document(item) for item in decision.reproduction.discrepancies)
    (diagnostics_directory / AnchorArtifactFileName.DISCREPANCIES.value).write_text(
        _encode_discrepancies(discrepancies), encoding="utf-8"
    )
    return checksum


def _encode_discrepancies(discrepancies: tuple[DiscrepancyDocument, ...]) -> str:
    from json import dumps

    return dumps([item.model_dump(mode="json") for item in discrepancies], sort_keys=True, separators=(",", ":"))


def gate_decision_document(decision: AnchorGateDecision) -> GateDecisionDocument:
    return GateDecisionDocument(
        status=decision.status.value,
        dependent_readiness=decision.dependent_readiness.value,
        blocking_discrepancies=tuple(discrepancy_document(item) for item in decision.blocking_discrepancies),
        declared_discrepancies=tuple(discrepancy_document(item) for item in decision.declared_discrepancies),
        reproduction=reproduction_document(decision.reproduction),
    )


def reproduction_document(reproduction: AnchorReproductionResult) -> ReproductionDocument:
    return ReproductionDocument(
        experiment=reproduction.experiment.value,
        evidence_role=reproduction.evidence_role.value,
        seed_cohort=_seed_cohort_values(reproduction.seed_cohort),
        reference_count=len(reproduction.references),
        observation_count=len(reproduction.observations),
        seed_subset=seed_subset_document(reproduction.seed_subset_comparison),
        metric_comparisons=tuple(comparison_document(item) for item in reproduction.metric_comparisons),
        discrepancies=tuple(discrepancy_document(item) for item in reproduction.discrepancies),
        dependency_blocker=dependency_blocker_document(reproduction.dependency_blocker),
    )


def _seed_cohort_values(cohort: SeedCohort) -> tuple[int, ...]:
    return tuple(seed.value for seed in cohort.values)


def seed_subset_document(comparison: AnchorSeedSubsetComparison) -> SeedSubsetComparisonDocument:
    return SeedSubsetComparisonDocument(
        expected_seeds=tuple(seed.value for seed in comparison.expected_seeds),
        observed_seeds=tuple(seed.value for seed in comparison.observed_seeds),
        decision=comparison.decision.value,
        reason=_optional_enum_value(comparison.reason),
    )


def dependency_blocker_document(blocker: AnchorDependencyBlocker | None) -> DependencyBlockerDocument | None:
    if blocker is None:
        return None
    return DependencyBlockerDocument(kind=blocker.kind.value, detail=blocker.detail)


def comparison_document(comparison: AnchorMetricComparison) -> MetricComparisonDocument:
    return MetricComparisonDocument(
        seed=comparison.reference.seed.value,
        threshold_method=comparison.reference.threshold_method.value,
        metric=comparison.reference.metric.value,
        expected=comparison.reference.value.value,
        observed=None if comparison.observation is None else comparison.observation.value.value,
        decision=comparison.decision.value,
        signed_difference=comparison.signed_difference,
        relative_difference=comparison.relative_difference,
        tolerance_strategy=comparison.tolerance_rule.strategy.value,
        reason=_optional_enum_value(comparison.reason),
    )


def discrepancy_document(discrepancy: AnchorDiscrepancy) -> DiscrepancyDocument:
    return DiscrepancyDocument(
        reason=discrepancy.reason.value,
        seed=None if discrepancy.seed is None else discrepancy.seed.value,
        threshold_method=_optional_enum_value(discrepancy.threshold_method),
        metric=_optional_enum_value(discrepancy.metric),
        expected_value=None if discrepancy.expected_value is None else discrepancy.expected_value.value,
        observed_value=None if discrepancy.observed_value is None else discrepancy.observed_value.value,
        signed_difference=discrepancy.signed_difference,
        relative_difference=discrepancy.relative_difference,
        tolerance_strategy=(None if discrepancy.tolerance_rule is None else discrepancy.tolerance_rule.strategy.value),
        artifact_path=None if discrepancy.artifact_path is None else discrepancy.artifact_path.as_posix(),
        artifact_checksum=None if discrepancy.artifact_checksum is None else discrepancy.artifact_checksum.value,
        detail=discrepancy.detail,
    )


def _optional_enum_value(value) -> str | None:
    return None if value is None else value.value
