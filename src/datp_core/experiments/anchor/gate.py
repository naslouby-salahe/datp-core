from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import (
    AnchorReproductionError,
    ErrorMessage,
)
from datp_core.core.identifiers import (
    ArtifactDirectoryPathText,
    ExperimentReadiness,
    FileContentText,
    PreprocessingProtocolId,
    Sha256Digest,
)
from datp_core.data.populations.declarations import split_protocol_for_population
from datp_core.experiments.anchor.contracts import (
    AnchorArtifactFileName,
    AnchorComparisonDecision,
    AnchorConfirmatoryHandoff,
    AnchorDiscrepancy,
    AnchorGateDecision,
    AnchorGateStatus,
    AnchorReproductionResult,
    VerifiedAnchorGateArtifact,
)
from datp_core.experiments.anchor.reproduction import (
    ANCHOR_EXPERIMENT,
    DECLARED_NON_BLOCKING_DISCREPANCY_REASONS,
)
from datp_core.experiments.graph import CONFIRMATORY_ENDPOINT
from datp_core.runtime.filesystem import write_text_atomically

_DECLARED_REASONS_SET = frozenset(DECLARED_NON_BLOCKING_DISCREPANCY_REASONS)


class AnchorArtifactValidationFailure(StrEnum):
    MISSING = "missing"
    CORRUPTED_OR_INVALID = "corrupted_or_invalid"
    STATUS_MISMATCH = "status_mismatch"
    DIRECTORY_MISMATCH = "directory_mismatch"
    STALE_OR_MISMATCHED = "stale_or_mismatched"


def decide_anchor_gate(reproduction: AnchorReproductionResult) -> AnchorGateDecision:
    blocking, declared = _partition_discrepancies(reproduction.discrepancies)
    mandatory_ok = _all_mandatory_comparisons_equivalent(reproduction)

    if reproduction.dependency_blocker is not None or blocking or not mandatory_ok:
        return AnchorGateDecision(
            status=AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            reproduction=reproduction,
            blocking_discrepancies=blocking or reproduction.discrepancies,
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
    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        return ExperimentReadiness.BLOCKED
    if decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}:
        return ExperimentReadiness.DECLARED
    raise AnchorReproductionError(
        ErrorMessage("unknown anchor gate status"),
        subject=decision.status,
    )


def assert_gate_not_bypassable(decision: AnchorGateDecision) -> AnchorGateDecision:
    if decision.dependent_readiness is ExperimentReadiness.EXECUTABLE:
        raise AnchorReproductionError(
            ErrorMessage("anchor gate cannot mark dependent experiments executable"),
            subject=decision.dependent_readiness,
        )
    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        _assert_blocked_gate_integrity(decision)
    return decision


def _assert_blocked_gate_integrity(decision: AnchorGateDecision) -> None:
    if decision.dependent_readiness is not ExperimentReadiness.BLOCKED:
        raise AnchorReproductionError(
            ErrorMessage("blocked anchor gate cannot permit dependent readiness"),
            subject=decision.status,
        )
    has_diagnostics = bool(decision.reproduction.discrepancies) or decision.reproduction.dependency_blocker is not None
    if not has_diagnostics:
        raise AnchorReproductionError(
            ErrorMessage("blocked anchor gate erased diagnostic state"),
            subject=decision.status,
        )


def _all_mandatory_comparisons_equivalent(reproduction: AnchorReproductionResult) -> bool:
    if reproduction.seed_subset_comparison.decision is not AnchorComparisonDecision.EQUIVALENT:
        return False

    if reproduction.bca_comparison.decision is not AnchorComparisonDecision.EQUIVALENT:
        return False

    comparisons = reproduction.metric_comparisons
    if not comparisons:
        return False

    return all(
        c.decision
        in {
            AnchorComparisonDecision.EQUIVALENT,
            AnchorComparisonDecision.DIAGNOSTIC_REPORTED,
        }
        for c in comparisons
    )


def _partition_discrepancies(
    discrepancies: tuple[AnchorDiscrepancy, ...],
) -> tuple[tuple[AnchorDiscrepancy, ...], tuple[AnchorDiscrepancy, ...]]:
    if not _DECLARED_REASONS_SET:
        return discrepancies, ()

    blocking: list[AnchorDiscrepancy] = []
    declared: list[AnchorDiscrepancy] = []

    for item in discrepancies:
        if item.reason in _DECLARED_REASONS_SET:
            declared.append(item)
        else:
            blocking.append(item)

    return tuple(blocking), tuple(declared)


def persist_anchor_gate_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> None:
    if diagnostics_directory is None:
        return

    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    write_text_atomically(
        diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value,
        FileContentText(canonical_json_text(decision)),
    )
    write_text_atomically(
        diagnostics_directory / AnchorArtifactFileName.DISCREPANCIES.value,
        FileContentText(canonical_json_text(decision.reproduction.discrepancies)),
    )
    handoff_path = diagnostics_directory / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value
    if decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}:
        handoff = build_anchor_confirmatory_handoff(decision=decision, diagnostics_directory=diagnostics_directory)
        write_text_atomically(
            handoff_path,
            FileContentText(canonical_json_text(handoff)),
        )
    elif handoff_path.exists():
        handoff_path.unlink()


def build_anchor_confirmatory_handoff(
    *,
    decision: AnchorGateDecision,
    diagnostics_directory: Path,
) -> AnchorConfirmatoryHandoff:
    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        raise AnchorReproductionError(
            ErrorMessage("blocked anchor gate cannot produce a confirmatory handoff"),
            subject=decision.status,
        )

    endpoint = CONFIRMATORY_ENDPOINT
    gate_path = diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value
    return validate_handoff_against_confirmatory_programme(
        AnchorConfirmatoryHandoff(
            anchor_experiment=ANCHOR_EXPERIMENT,
            anchor_seed_cohort=decision.reproduction.seed_cohort,
            dependent_confirmatory_experiment=endpoint.experiment,
            dependent_population=endpoint.population,
            dependent_model=endpoint.training_model,
            dependent_seed_cohort=endpoint.seed_cohort,
            split_protocol_identity=split_protocol_for_population(endpoint.population),
            preprocessing_protocol_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            threshold_protocol_identities=(endpoint.shared_threshold, endpoint.local_threshold),
            verified_gate_status=decision.status,
            diagnostics_directory=ArtifactDirectoryPathText(str(diagnostics_directory.resolve())),
            gate_decision_sha256=_sha256_file(gate_path),
        )
    )


def load_verified_anchor_gate_artifact(diagnostics_directory: Path) -> VerifiedAnchorGateArtifact:
    decision = _load_gate_decision(diagnostics_directory)
    decision = assert_gate_not_bypassable(decision)

    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        raise AnchorReproductionError(
            ErrorMessage("anchor gate is blocked and cannot permit confirmatory claims"),
            subject=decision.status,
        )

    return VerifiedAnchorGateArtifact(
        decision=decision,
        diagnostics_directory=ArtifactDirectoryPathText(str(diagnostics_directory.resolve())),
    )


def load_anchor_gate_decision(diagnostics_directory: Path) -> AnchorGateDecision:
    return assert_gate_not_bypassable(_load_gate_decision(diagnostics_directory))


def load_anchor_confirmatory_handoff(
    diagnostics_directory: Path,
    *,
    verified_gate: VerifiedAnchorGateArtifact,
) -> AnchorConfirmatoryHandoff:
    if not diagnostics_directory.is_dir() or diagnostics_directory.is_symlink():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate diagnostics directory is missing: {diagnostics_directory}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    handoff_path = diagnostics_directory / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value

    if not handoff_path.is_file() or handoff_path.is_symlink():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff artifact is missing: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    try:
        handoff = AnchorConfirmatoryHandoff.model_validate_json(handoff_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff is corrupted or schema-invalid: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.CORRUPTED_OR_INVALID,
        ) from error

    if handoff.verified_gate_status is not verified_gate.decision.status:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff gate status does not match the verified gate: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.STATUS_MISMATCH,
        )

    gate_path = diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value
    if not gate_path.is_file() or gate_path.is_symlink():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate decision artifact is missing or unsafe: {gate_path}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )
    loaded_gate = _load_gate_decision(diagnostics_directory)
    if loaded_gate != verified_gate.decision:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff is not bound to the verified gate: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.STALE_OR_MISMATCHED,
        )
    if handoff.gate_decision_sha256 != _sha256_file(gate_path):
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff gate digest does not match the gate decision: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.STALE_OR_MISMATCHED,
        )

    if str(handoff.diagnostics_directory) != str(diagnostics_directory.resolve()):
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff diagnostics directory is mismatched: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.DIRECTORY_MISMATCH,
        )

    return validate_handoff_against_confirmatory_programme(handoff)


def validate_handoff_against_confirmatory_programme(
    handoff: AnchorConfirmatoryHandoff,
) -> AnchorConfirmatoryHandoff:
    endpoint = CONFIRMATORY_ENDPOINT
    mismatches: list[str] = []

    if handoff.dependent_confirmatory_experiment is not endpoint.experiment:
        mismatches.append("dependent_confirmatory_experiment")
    if handoff.dependent_population is not endpoint.population:
        mismatches.append("dependent_population")
    if handoff.dependent_model is not endpoint.training_model:
        mismatches.append("dependent_model")
    if handoff.dependent_seed_cohort != endpoint.seed_cohort:
        mismatches.append("dependent_seed_cohort")
    if handoff.preprocessing_protocol_identity is not PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD:
        mismatches.append("preprocessing_protocol_identity")
    if handoff.threshold_protocol_identities != (endpoint.shared_threshold, endpoint.local_threshold):
        mismatches.append("threshold_protocol_identities")

    if handoff.split_protocol_identity is not split_protocol_for_population(endpoint.population):
        mismatches.append("split_protocol_identity")
    if mismatches:
        raise AnchorReproductionError(
            ErrorMessage(
                "anchor confirmatory handoff is stale relative to the locked confirmatory programme: "
                + ",".join(mismatches)
            ),
            reason=AnchorArtifactValidationFailure.STALE_OR_MISMATCHED,
        )

    return handoff


def _load_gate_decision(diagnostics_directory: Path) -> AnchorGateDecision:
    if not diagnostics_directory.is_dir() or diagnostics_directory.is_symlink():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate diagnostics directory is missing: {diagnostics_directory}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    gate_path = diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value
    if not gate_path.is_file() or gate_path.is_symlink():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate decision artifact is missing: {gate_path}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    try:
        decision = AnchorGateDecision.model_validate_json(gate_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate decision artifact is corrupted or schema-invalid: {gate_path}"),
            reason=AnchorArtifactValidationFailure.CORRUPTED_OR_INVALID,
        ) from error

    return decision


def _sha256_file(path: Path) -> Sha256Digest:
    return Sha256Digest(sha256(path.read_bytes()).hexdigest())
