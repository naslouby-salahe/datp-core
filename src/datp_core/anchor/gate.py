"""Gate decision for historical anchor reproduction and dependent-experiment readiness."""

from pathlib import Path

from datp_core.anchor.models import (
    DECLARED_NON_BLOCKING_DISCREPANCY_REASONS,
    AnchorArtifactFileName,
    AnchorComparisonDecision,
    AnchorDiscrepancy,
    AnchorGateDecision,
    AnchorGateStatus,
    AnchorReproductionResult,
)
from datp_core.domain.enums import ExperimentReadiness
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_text


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
    gate_json = canonical_json_text(decision)
    checksum = checksum_text(gate_json)
    if diagnostics_directory is None:
        return checksum
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    (diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value).write_text(gate_json, encoding="utf-8")
    discrepancies_json = canonical_json_text(decision.reproduction.discrepancies)
    (diagnostics_directory / AnchorArtifactFileName.DISCREPANCIES.value).write_text(
        discrepancies_json,
        encoding="utf-8",
    )
    return checksum
