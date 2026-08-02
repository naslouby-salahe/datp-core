"""Gate decision for historical anchor reproduction and dependent-experiment readiness."""

from json import dumps
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
from datp_core.domain.enums import ExperimentReadiness
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Checksum, checksum_text


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


def persist_anchor_gate_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> Checksum:
    """Write gate decision and discrepancy diagnostics, returning a deterministic checksum."""
    gate_payload = _serialize_gate_decision(decision)
    gate_json = dumps(gate_payload, sort_keys=True, separators=(",", ":"))
    checksum = checksum_text(gate_json)
    if diagnostics_directory is None:
        return checksum
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    (diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value).write_text(gate_json, encoding="utf-8")
    discrepancies_json = dumps(
        [_serialize_discrepancy(item) for item in decision.reproduction.discrepancies],
        sort_keys=True,
        separators=(",", ":"),
    )
    (diagnostics_directory / AnchorArtifactFileName.DISCREPANCIES.value).write_text(
        discrepancies_json, encoding="utf-8"
    )
    return checksum


def _serialize_gate_decision(decision: AnchorGateDecision) -> dict:
    return {
        "status": decision.status.value,
        "dependent_readiness": decision.dependent_readiness.value,
        "blocking_discrepancies": [_serialize_discrepancy(d) for d in decision.blocking_discrepancies],
        "declared_discrepancies": [_serialize_discrepancy(d) for d in decision.declared_discrepancies],
        "reproduction": _serialize_reproduction(decision.reproduction),
    }


def _serialize_reproduction(reproduction: AnchorReproductionResult) -> dict:
    return {
        "experiment": reproduction.experiment.value,
        "evidence_role": reproduction.evidence_role.value,
        "seed_cohort": [s.value for s in reproduction.seed_cohort.values],
        "reference_count": len(reproduction.references),
        "observation_count": len(reproduction.observations),
        "seed_subset": _serialize_seed_subset(reproduction.seed_subset_comparison),
        "metric_comparisons": [_serialize_metric_comparison(c) for c in reproduction.metric_comparisons],
        "discrepancies": [_serialize_discrepancy(d) for d in reproduction.discrepancies],
        "dependency_blocker": _serialize_dependency_blocker(reproduction.dependency_blocker),
    }


def _serialize_seed_subset(comparison: AnchorSeedSubsetComparison) -> dict:
    return {
        "expected_seeds": [s.value for s in comparison.expected_seeds],
        "observed_seeds": [s.value for s in comparison.observed_seeds],
        "decision": comparison.decision.value,
        "reason": comparison.reason.value if comparison.reason is not None else None,
    }


def _serialize_dependency_blocker(blocker: AnchorDependencyBlocker | None) -> dict | None:
    if blocker is None:
        return None
    return {"kind": blocker.kind.value, "detail": blocker.detail}


def _serialize_metric_comparison(comparison: AnchorMetricComparison) -> dict:
    return {
        "seed": comparison.reference.seed.value,
        "threshold_method": comparison.reference.threshold_method.value,
        "metric": comparison.reference.metric.value,
        "expected": comparison.reference.value.value,
        "observed": comparison.observation.value.value if comparison.observation is not None else None,
        "decision": comparison.decision.value,
        "signed_difference": comparison.signed_difference,
        "relative_difference": comparison.relative_difference,
        "tolerance_strategy": comparison.tolerance_rule.strategy.value,
        "reason": comparison.reason.value if comparison.reason is not None else None,
    }


def _serialize_discrepancy(discrepancy: AnchorDiscrepancy) -> dict:
    return {
        "reason": discrepancy.reason.value,
        "seed": discrepancy.seed.value if discrepancy.seed is not None else None,
        "threshold_method": discrepancy.threshold_method.value if discrepancy.threshold_method is not None else None,
        "metric": discrepancy.metric.value if discrepancy.metric is not None else None,
        "expected_value": discrepancy.expected_value.value if discrepancy.expected_value is not None else None,
        "observed_value": discrepancy.observed_value.value if discrepancy.observed_value is not None else None,
        "signed_difference": discrepancy.signed_difference,
        "relative_difference": discrepancy.relative_difference,
        "tolerance_strategy": (
            discrepancy.tolerance_rule.strategy.value if discrepancy.tolerance_rule is not None else None
        ),
        "artifact_path": discrepancy.artifact_path.as_posix() if discrepancy.artifact_path is not None else None,
        "artifact_checksum": discrepancy.artifact_checksum.value if discrepancy.artifact_checksum is not None else None,
        "detail": discrepancy.detail,
    }
