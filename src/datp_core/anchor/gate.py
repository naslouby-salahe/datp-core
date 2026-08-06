"""Gate decision for historical anchor reproduction and dependent-experiment readiness."""

from enum import StrEnum
from pathlib import Path

from pydantic import model_validator

from datp_core.anchor.comparison import AnchorComparisonDecision, AnchorDiscrepancy
from datp_core.anchor.reproduction import (
    DECLARED_NON_BLOCKING_DISCREPANCY_REASONS,
    AnchorArtifactFileName,
    AnchorReproductionResult,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import ExperimentReadiness
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_text


class AnchorGateStatus(StrEnum):
    PASS = "pass"
    PASS_WITH_DECLARED_DISCREPANCY = "pass_with_declared_discrepancy"
    BLOCKED = "blocked"


class AnchorGateDecision(StrictModel):
    status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    reproduction: AnchorReproductionResult
    blocking_discrepancies: tuple[AnchorDiscrepancy, ...]
    declared_discrepancies: tuple[AnchorDiscrepancy, ...]

    @model_validator(mode="after")
    def validate_gate_integrity(self) -> "AnchorGateDecision":
        match self.status:
            case AnchorGateStatus.PASS:
                _require_clean_pass(self)
            case AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY:
                _require_declared_discrepancy_pass(self)
            case AnchorGateStatus.BLOCKED:
                _require_blocked_gate(self)
        return self


def _require_clean_pass(decision: AnchorGateDecision) -> None:
    if decision.blocking_discrepancies or decision.declared_discrepancies:
        raise ValueError("PASS forbids discrepancies")
    if decision.dependent_readiness is not ExperimentReadiness.DECLARED:
        raise ValueError("PASS permits only declared dependent readiness handoff")


def _require_declared_discrepancy_pass(decision: AnchorGateDecision) -> None:
    if decision.blocking_discrepancies or not decision.declared_discrepancies:
        raise ValueError("PASS_WITH_DECLARED_DISCREPANCY requires only declared discrepancies")
    if decision.dependent_readiness is not ExperimentReadiness.DECLARED:
        raise ValueError("declared-discrepancy pass still only unlocks declared dependent readiness")


def _require_blocked_gate(decision: AnchorGateDecision) -> None:
    if not decision.blocking_discrepancies and decision.reproduction.dependency_blocker is None:
        raise ValueError("BLOCKED requires blocking discrepancies or a dependency blocker")
    if decision.dependent_readiness is not ExperimentReadiness.BLOCKED:
        raise ValueError("blocked anchor gate must block dependent readiness")


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


class AnchorGateCompletionMarker(StrictModel):
    artifact_checksum: Checksum
    status: AnchorGateStatus


class VerifiedAnchorGateArtifact(StrictModel):
    """Checksum-verified anchor-gate artifact that claim export must consume."""

    decision: AnchorGateDecision
    artifact_checksum: Checksum
    diagnostics_directory: str

    @model_validator(mode="after")
    def validate_passed_gate(self) -> "VerifiedAnchorGateArtifact":
        if self.decision.status is AnchorGateStatus.BLOCKED:
            raise ValueError("verified anchor-gate artifact cannot be blocked")
        recomputed = checksum_text(canonical_json_text(self.decision))
        if recomputed != self.artifact_checksum:
            raise ValueError("anchor-gate artifact checksum does not match the decision payload")
        return self

    @property
    def permits_confirmatory_claims(self) -> bool:
        return self.decision.status in {
            AnchorGateStatus.PASS,
            AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
        }


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
    marker = AnchorGateCompletionMarker(artifact_checksum=checksum, status=decision.status)
    (diagnostics_directory / AnchorArtifactFileName.GATE_COMPLETION.value).write_text(
        canonical_json_text(marker),
        encoding="utf-8",
    )
    return checksum


def load_verified_anchor_gate_artifact(diagnostics_directory: Path) -> VerifiedAnchorGateArtifact:
    """Load, re-validate, and checksum-verify a persisted anchor-gate decision.

    Fail-closed on missing, corrupted, stale, or blocked gate artifacts.
    Manual boolean success cannot be asserted through this path.
    """
    if not diagnostics_directory.is_dir():
        raise AnchorReproductionError(
            "anchor-gate diagnostics directory is missing",
            reason=str(diagnostics_directory),
        )
    gate_path = diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value
    if not gate_path.is_file():
        raise AnchorReproductionError(
            "anchor-gate decision artifact is missing",
            reason=str(gate_path),
        )
    payload = gate_path.read_text(encoding="utf-8")
    try:
        decision = AnchorGateDecision.model_validate_json(payload)
    except (ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            "anchor-gate decision artifact is corrupted or schema-invalid",
            reason=str(gate_path),
        ) from error
    decision = assert_gate_not_bypassable(decision)
    artifact_checksum = checksum_text(canonical_json_text(decision))
    marker_path = diagnostics_directory / AnchorArtifactFileName.GATE_COMPLETION.value
    if not marker_path.is_file():
        raise AnchorReproductionError(
            "anchor-gate completion marker is missing",
            reason=str(marker_path),
        )
    try:
        marker = AnchorGateCompletionMarker.model_validate_json(marker_path.read_text(encoding="utf-8"))
    except (ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            "anchor-gate completion marker is corrupted or schema-invalid",
            reason=str(marker_path),
        ) from error
    if marker.artifact_checksum != artifact_checksum or marker.status is not decision.status:
        raise AnchorReproductionError(
            "anchor-gate completion marker is stale or mismatched",
            reason=str(marker_path),
        )
    if decision.status is AnchorGateStatus.BLOCKED:
        raise AnchorReproductionError(
            "anchor gate is blocked and cannot permit confirmatory claims",
            subject=decision.status,
        )
    return VerifiedAnchorGateArtifact(
        decision=decision,
        artifact_checksum=artifact_checksum,
        diagnostics_directory=str(diagnostics_directory.resolve()),
    )
