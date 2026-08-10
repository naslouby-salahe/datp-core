from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError

from datp_core.analysis.metrics.protocols import CONFIRMATORY_METRICS
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_checksum, canonical_json_text
from datp_core.core.errors import (
    AnchorReproductionError,
    ErrorMessage,
)
from datp_core.core.identifiers import (
    ArtifactDirectoryPathText,
    ExperimentReadiness,
    PreprocessingProtocolId,
    ScoreFrameColumn,
)
from datp_core.data.populations.declarations import split_protocol_for_population
from datp_core.detector.checkpoints.protocols import ANCHOR_CHECKPOINT_PROTOCOL, ANCHOR_CHECKPOINT_SELECTION_RULE
from datp_core.detector.training.protocols import ANCHOR_NBAIOT_AUTOENCODER
from datp_core.experiments.anchor.contracts import (
    AnchorArtifactFileName,
    AnchorComparisonDecision,
    AnchorConfirmatoryHandoff,
    AnchorDiscrepancy,
    AnchorGateCompletionMarker,
    AnchorGateDecision,
    AnchorGateStatus,
    AnchorReproductionResult,
    VerifiedAnchorGateArtifact,
)
from datp_core.experiments.anchor.reproduction import (
    ANCHOR_EXPERIMENT,
    DECLARED_NON_BLOCKING_DISCREPANCY_REASONS,
)
from datp_core.experiments.anchor.spec import ANCHOR_DECISION_PROTOCOL
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.experiments.graph import CONFIRMATORY_ENDPOINT

_DECLARED_REASONS_SET = frozenset(DECLARED_NON_BLOCKING_DISCREPANCY_REASONS)


class AnchorArtifactValidationFailure(StrEnum):
    MISSING = "missing"
    CORRUPTED_OR_INVALID = "corrupted_or_invalid"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    STATUS_MISMATCH = "status_mismatch"
    DIRECTORY_MISMATCH = "directory_mismatch"
    STALE_OR_MISMATCHED = "stale_or_mismatched"


def decide_anchor_gate(reproduction: AnchorReproductionResult) -> AnchorGateDecision:
    """Derive an irreversible gate decision from a typed reproduction result."""
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
    """Map gate status to dependent-experiment readiness. No caller override is accepted."""
    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        return ExperimentReadiness.BLOCKED
    if decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}:
        return ExperimentReadiness.DECLARED
    raise AnchorReproductionError(
        ErrorMessage("unknown anchor gate status"),
        subject=decision.status,
    )


def assert_gate_not_bypassable(decision: AnchorGateDecision) -> AnchorGateDecision:
    """Structural guard: blocked gates never expose claim-permitted dependent readiness."""
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

    # The roadmap gate carries no per-seed value condition (conditions 1-10 are
    # identity checks, 11-13 are the cohort-level BCa interval). Per-seed
    # comparisons must be present and structurally valid; exact matches are
    # EQUIVALENT, and any deviation is reported as DIAGNOSTIC_REPORTED rather
    # than blocking the gate.
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
    """Split discrepancies into blocking vs declared non-blocking classes."""
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


def persist_anchor_gate_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> Checksum:
    """Write gate decision, discrepancy diagnostics, and PASS handoff, returning gate checksum."""
    gate_json = canonical_json_text(decision)
    checksum = Checksum.from_text(gate_json)

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

    if decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}:
        handoff = build_anchor_confirmatory_handoff(
            decision=decision,
            gate_checksum=checksum,
            diagnostics_directory=diagnostics_directory,
        )
        (diagnostics_directory / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value).write_text(
            canonical_json_text(handoff),
            encoding="utf-8",
        )

    return checksum


def build_anchor_confirmatory_handoff(
    *,
    decision: AnchorGateDecision,
    gate_checksum: Checksum,
    diagnostics_directory: Path,
) -> AnchorConfirmatoryHandoff:
    """Construct the typed programme-binding handoff for a permitting gate decision."""
    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        raise AnchorReproductionError(
            ErrorMessage("blocked anchor gate cannot produce a confirmatory handoff"),
            subject=decision.status,
        )

    endpoint = CONFIRMATORY_ENDPOINT
    references_observations_checksum = canonical_checksum(
        {
            "references": decision.reproduction.references,
            "observations": decision.reproduction.observations,
        }
    )

    inventory_checksum = _complete_artifact_inventory_checksum(
        gate_checksum=gate_checksum,
        discrepancies_checksum=Checksum.from_text(canonical_json_text(decision.reproduction.discrepancies)),
        references_observations_checksum=references_observations_checksum,
        observation_artifact_checksums=tuple(item.artifact_checksum for item in decision.reproduction.observations),
    )

    binding = {
        "anchor_experiment": ANCHOR_EXPERIMENT,
        "anchor_seed_cohort": decision.reproduction.seed_cohort,
        "anchor_protocol_checksum": canonical_checksum(ANCHOR_DECISION_PROTOCOL),
        "anchor_references_observations_checksum": references_observations_checksum,
        "anchor_gate_decision_checksum": gate_checksum,
        "dependent_confirmatory_experiment": endpoint.experiment,
        "dependent_population": endpoint.population,
        "dependent_model": endpoint.training_model,
        "dependent_seed_cohort": endpoint.seed_cohort,
        "split_protocol_identity": split_protocol_for_population(endpoint.population),
        "preprocessing_protocol_identity": PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        "checkpoint_protocol_identity": _checkpoint_protocol_identity(),
        "scoring_protocol_identity": _scoring_protocol_identity(),
        "threshold_protocol_identities": (
            endpoint.shared_threshold,
            endpoint.local_threshold,
        ),
        "evaluation_protocol_identity": _evaluation_protocol_identity(),
        "confirmatory_inference_protocol_identity": canonical_checksum(CONFIRMATORY_INFERENCE_PROTOCOL),
        "complete_artifact_inventory_checksum": inventory_checksum,
        "verified_gate_status": decision.status,
        "verified_gate_artifact_checksum": gate_checksum,
        "diagnostics_directory": ArtifactDirectoryPathText(str(diagnostics_directory.resolve())),
    }

    return validate_handoff_against_confirmatory_programme(
        AnchorConfirmatoryHandoff(
            creation_identity=canonical_checksum(binding),
            anchor_experiment=ANCHOR_EXPERIMENT,
            anchor_seed_cohort=decision.reproduction.seed_cohort,
            anchor_protocol_checksum=canonical_checksum(ANCHOR_DECISION_PROTOCOL),
            anchor_references_observations_checksum=references_observations_checksum,
            anchor_gate_decision_checksum=gate_checksum,
            dependent_confirmatory_experiment=endpoint.experiment,
            dependent_population=endpoint.population,
            dependent_model=endpoint.training_model,
            dependent_seed_cohort=endpoint.seed_cohort,
            split_protocol_identity=split_protocol_for_population(endpoint.population),
            preprocessing_protocol_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            checkpoint_protocol_identity=_checkpoint_protocol_identity(),
            scoring_protocol_identity=_scoring_protocol_identity(),
            threshold_protocol_identities=(endpoint.shared_threshold, endpoint.local_threshold),
            evaluation_protocol_identity=_evaluation_protocol_identity(),
            confirmatory_inference_protocol_identity=canonical_checksum(CONFIRMATORY_INFERENCE_PROTOCOL),
            complete_artifact_inventory_checksum=inventory_checksum,
            verified_gate_status=decision.status,
            verified_gate_artifact_checksum=gate_checksum,
            diagnostics_directory=ArtifactDirectoryPathText(str(diagnostics_directory.resolve())),
        )
    )


def load_verified_anchor_gate_artifact(diagnostics_directory: Path) -> VerifiedAnchorGateArtifact:
    """Load, re-validate, and checksum-verify a persisted anchor-gate decision.

    Fail-closed on missing, corrupted, stale, or blocked gate artifacts.
    Manual boolean success cannot be asserted through this path.
    """
    decision, artifact_checksum = _load_gate_decision_and_checksum(diagnostics_directory)
    decision = assert_gate_not_bypassable(decision)

    if decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
        raise AnchorReproductionError(
            ErrorMessage("anchor gate is blocked and cannot permit confirmatory claims"),
            subject=decision.status,
        )

    return VerifiedAnchorGateArtifact(
        decision=decision,
        artifact_checksum=artifact_checksum,
        diagnostics_directory=ArtifactDirectoryPathText(str(diagnostics_directory.resolve())),
    )


def load_anchor_gate_decision(diagnostics_directory: Path) -> AnchorGateDecision:
    """Load a persisted gate decision without claim-permit filtering (inspect path)."""
    decision, _ = _load_gate_decision_and_checksum(diagnostics_directory)
    return assert_gate_not_bypassable(decision)


def load_anchor_confirmatory_handoff(
    diagnostics_directory: Path,
    *,
    verified_gate: VerifiedAnchorGateArtifact,
) -> AnchorConfirmatoryHandoff:
    """Load and validate the typed confirmatory handoff bound to a verified gate."""
    if not diagnostics_directory.is_dir():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate diagnostics directory is missing: {diagnostics_directory}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    handoff_path = diagnostics_directory / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value

    if not handoff_path.is_file():
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

    if handoff.verified_gate_artifact_checksum != verified_gate.artifact_checksum:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff does not match the verified gate checksum: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.CHECKSUM_MISMATCH,
        )

    if handoff.verified_gate_status is not verified_gate.decision.status:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor confirmatory handoff gate status does not match the verified gate: {handoff_path}"),
            reason=AnchorArtifactValidationFailure.STATUS_MISMATCH,
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
    """Fail closed when the handoff no longer matches the locked confirmatory programme."""
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
    if handoff.checkpoint_protocol_identity != _checkpoint_protocol_identity():
        mismatches.append("checkpoint_protocol_identity")
    if handoff.scoring_protocol_identity != _scoring_protocol_identity():
        mismatches.append("scoring_protocol_identity")
    if handoff.evaluation_protocol_identity != _evaluation_protocol_identity():
        mismatches.append("evaluation_protocol_identity")
    if handoff.confirmatory_inference_protocol_identity != canonical_checksum(CONFIRMATORY_INFERENCE_PROTOCOL):
        mismatches.append("confirmatory_inference_protocol_identity")
    if handoff.anchor_protocol_checksum != canonical_checksum(ANCHOR_DECISION_PROTOCOL):
        mismatches.append("anchor_protocol_checksum")

    if mismatches:
        raise AnchorReproductionError(
            ErrorMessage(
                "anchor confirmatory handoff is stale relative to the locked confirmatory programme: "
                + ",".join(mismatches)
            ),
            reason=AnchorArtifactValidationFailure.STALE_OR_MISMATCHED,
        )

    return handoff


def _load_gate_decision_and_checksum(diagnostics_directory: Path) -> tuple[AnchorGateDecision, Checksum]:
    if not diagnostics_directory.is_dir():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate diagnostics directory is missing: {diagnostics_directory}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    gate_path = diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value
    if not gate_path.is_file():
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

    artifact_checksum = Checksum.from_text(canonical_json_text(decision))

    marker_path = diagnostics_directory / AnchorArtifactFileName.GATE_COMPLETION.value
    if not marker_path.is_file():
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate completion marker is missing: {marker_path}"),
            reason=AnchorArtifactValidationFailure.MISSING,
        )

    try:
        marker = AnchorGateCompletionMarker.model_validate_json(marker_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate completion marker is corrupted or schema-invalid: {marker_path}"),
            reason=AnchorArtifactValidationFailure.CORRUPTED_OR_INVALID,
        ) from error

    if marker.artifact_checksum != artifact_checksum or marker.status is not decision.status:
        raise AnchorReproductionError(
            ErrorMessage(f"anchor-gate completion marker is stale or mismatched: {marker_path}"),
            reason=AnchorArtifactValidationFailure.STALE_OR_MISMATCHED,
        )

    return decision, artifact_checksum


def _checkpoint_protocol_identity() -> Checksum:
    return canonical_checksum(
        {
            "checkpoint_protocol": ANCHOR_CHECKPOINT_PROTOCOL,
            "selection_rule": ANCHOR_CHECKPOINT_SELECTION_RULE,
        }
    )


def _scoring_protocol_identity() -> Checksum:
    return canonical_checksum(
        {
            "score_column": ScoreFrameColumn.RECONSTRUCTION_ERROR,
            "autoencoder": ANCHOR_NBAIOT_AUTOENCODER,
        }
    )


def _evaluation_protocol_identity() -> Checksum:
    return canonical_checksum(
        {
            "primary_metric": CONFIRMATORY_ENDPOINT.metric,
            "metrics": CONFIRMATORY_METRICS,
        }
    )


def _complete_artifact_inventory_checksum(
    *,
    gate_checksum: Checksum,
    discrepancies_checksum: Checksum,
    references_observations_checksum: Checksum,
    observation_artifact_checksums: tuple[Checksum, ...],
) -> Checksum:
    return canonical_checksum(
        {
            "gate_decision": gate_checksum,
            "discrepancies": discrepancies_checksum,
            "references_observations": references_observations_checksum,
            "observation_artifacts": observation_artifact_checksums,
        }
    )
