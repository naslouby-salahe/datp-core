"""Gate decision for historical anchor reproduction and dependent-experiment readiness."""

from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError, model_validator

from datp_core.anchor.comparison import AnchorComparisonDecision, AnchorDiscrepancy
from datp_core.anchor.reproduction import (
    ANCHOR_EXPERIMENT,
    DECLARED_NON_BLOCKING_DISCREPANCY_REASONS,
    AnchorArtifactFileName,
    AnchorReproductionResult,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.provenance import canonical_checksum, canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from datp_core.protocols.metrics import CONFIRMATORY_METRICS
from datp_core.protocols.populations import split_protocol_for_population
from datp_core.protocols.seeds import SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.protocols.training import CHECKPOINT_PROTOCOL, CHECKPOINT_SELECTION_RULE, NBAIOT_AUTOENCODER
from datp_core.protocols.validation import CONFIRMATORY_ENDPOINT


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


class AnchorHandoffSchemaIdentity(StrEnum):
    V1 = "anchor_confirmatory_handoff.v1"


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


class AnchorConfirmatoryHandoff(StrictModel):
    """Typed anchor→confirmatory binding artifact that locks programme identity."""

    schema_identity: AnchorHandoffSchemaIdentity
    creation_identity: Checksum
    anchor_experiment: ExperimentId
    anchor_seed_cohort: SeedCohort
    anchor_protocol_checksum: Checksum
    anchor_references_observations_checksum: Checksum
    anchor_gate_decision_checksum: Checksum
    dependent_confirmatory_experiment: ExperimentId
    dependent_population: PopulationId
    dependent_model: TrainingModelId
    dependent_seed_cohort: SeedCohort
    split_protocol_identity: SplitProtocolId
    preprocessing_protocol_identity: PreprocessingProtocolId
    checkpoint_protocol_identity: Checksum
    scoring_protocol_identity: Checksum
    threshold_protocol_identities: tuple[FederatedThresholdMethod, ...]
    evaluation_protocol_identity: Checksum
    confirmatory_inference_protocol_identity: Checksum
    complete_artifact_inventory_checksum: Checksum
    verified_gate_status: AnchorGateStatus
    verified_gate_artifact_checksum: Checksum
    diagnostics_directory: str

    @model_validator(mode="after")
    def validate_handoff_integrity(self) -> "AnchorConfirmatoryHandoff":
        if self.schema_identity is not AnchorHandoffSchemaIdentity.V1:
            raise ValueError("unsupported anchor confirmatory handoff schema")
        if self.anchor_experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("handoff anchor experiment must be historical DATP reproduction")
        if self.dependent_confirmatory_experiment is not ExperimentId.SHARED_VS_LOCAL_CONFIRMATION:
            raise ValueError("handoff dependent experiment must be shared-vs-local confirmation")
        if self.verified_gate_status is AnchorGateStatus.BLOCKED:
            raise ValueError("confirmatory handoff cannot bind a blocked gate")
        if self.verified_gate_status not in {
            AnchorGateStatus.PASS,
            AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
        }:
            raise ValueError("confirmatory handoff requires a permitting gate status")
        if self.anchor_gate_decision_checksum != self.verified_gate_artifact_checksum:
            raise ValueError("handoff gate decision checksum must match verified gate artifact checksum")
        if not self.threshold_protocol_identities:
            raise ValueError("handoff requires at least one threshold protocol identity")
        if not self.diagnostics_directory.strip():
            raise ValueError("handoff diagnostics directory must be non-empty")
        recomputed = _handoff_creation_identity(self)
        if recomputed != self.creation_identity:
            raise ValueError("handoff creation identity does not match the binding payload")
        return self


def persist_anchor_gate_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> Checksum:
    """Write gate decision, discrepancy diagnostics, and PASS handoff, returning gate checksum."""
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
    if decision.status is AnchorGateStatus.BLOCKED:
        raise AnchorReproductionError(
            "blocked anchor gate cannot produce a confirmatory handoff",
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
        discrepancies_checksum=checksum_text(canonical_json_text(decision.reproduction.discrepancies)),
        references_observations_checksum=references_observations_checksum,
        observation_artifact_checksums=tuple(item.artifact_checksum for item in decision.reproduction.observations),
    )
    binding = {
        "schema_identity": AnchorHandoffSchemaIdentity.V1,
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
        "diagnostics_directory": str(diagnostics_directory.resolve()),
    }
    creation_identity = canonical_checksum(binding)
    return AnchorConfirmatoryHandoff(creation_identity=creation_identity, **binding)


def load_verified_anchor_gate_artifact(diagnostics_directory: Path) -> VerifiedAnchorGateArtifact:
    """Load, re-validate, and checksum-verify a persisted anchor-gate decision.

    Fail-closed on missing, corrupted, stale, or blocked gate artifacts.
    Manual boolean success cannot be asserted through this path.
    """
    decision, artifact_checksum = _load_gate_decision_and_checksum(diagnostics_directory)
    decision = assert_gate_not_bypassable(decision)
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


def load_anchor_gate_decision(diagnostics_directory: Path) -> AnchorGateDecision:
    """Load a persisted gate decision without claim-permit filtering (inspect path)."""
    decision, _checksum = _load_gate_decision_and_checksum(diagnostics_directory)
    return assert_gate_not_bypassable(decision)


def load_anchor_confirmatory_handoff(
    diagnostics_directory: Path,
    *,
    verified_gate: VerifiedAnchorGateArtifact,
) -> AnchorConfirmatoryHandoff:
    """Load and validate the typed confirmatory handoff bound to a verified gate."""
    if not diagnostics_directory.is_dir():
        raise AnchorReproductionError(
            "anchor-gate diagnostics directory is missing",
            reason=str(diagnostics_directory),
        )
    handoff_path = diagnostics_directory / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value
    if not handoff_path.is_file():
        raise AnchorReproductionError(
            "anchor confirmatory handoff artifact is missing",
            reason=str(handoff_path),
        )
    try:
        handoff = AnchorConfirmatoryHandoff.model_validate_json(handoff_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            "anchor confirmatory handoff is corrupted or schema-invalid",
            reason=str(handoff_path),
        ) from error
    if handoff.verified_gate_artifact_checksum != verified_gate.artifact_checksum:
        raise AnchorReproductionError(
            "anchor confirmatory handoff does not match the verified gate checksum",
            reason=str(handoff_path),
        )
    if handoff.verified_gate_status is not verified_gate.decision.status:
        raise AnchorReproductionError(
            "anchor confirmatory handoff gate status does not match the verified gate",
            reason=str(handoff_path),
        )
    if handoff.diagnostics_directory != str(diagnostics_directory.resolve()):
        raise AnchorReproductionError(
            "anchor confirmatory handoff diagnostics directory is mismatched",
            reason=str(handoff_path),
        )
    return validate_handoff_against_confirmatory_programme(handoff)


def validate_handoff_against_confirmatory_programme(
    handoff: AnchorConfirmatoryHandoff,
) -> AnchorConfirmatoryHandoff:
    """Fail closed when the handoff no longer matches the locked confirmatory programme."""
    endpoint = CONFIRMATORY_ENDPOINT
    expected_split = split_protocol_for_population(endpoint.population)
    expected_checkpoint = _checkpoint_protocol_identity()
    expected_scoring = _scoring_protocol_identity()
    expected_evaluation = _evaluation_protocol_identity()
    expected_inference = canonical_checksum(CONFIRMATORY_INFERENCE_PROTOCOL)
    expected_thresholds = (endpoint.shared_threshold, endpoint.local_threshold)
    mismatches: list[str] = []
    if handoff.dependent_confirmatory_experiment is not endpoint.experiment:
        mismatches.append("dependent_confirmatory_experiment")
    if handoff.dependent_population is not endpoint.population:
        mismatches.append("dependent_population")
    if handoff.dependent_model is not endpoint.training_model:
        mismatches.append("dependent_model")
    if handoff.dependent_seed_cohort != endpoint.seed_cohort:
        mismatches.append("dependent_seed_cohort")
    if handoff.split_protocol_identity is not expected_split:
        mismatches.append("split_protocol_identity")
    if handoff.preprocessing_protocol_identity is not PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD:
        mismatches.append("preprocessing_protocol_identity")
    if handoff.checkpoint_protocol_identity != expected_checkpoint:
        mismatches.append("checkpoint_protocol_identity")
    if handoff.scoring_protocol_identity != expected_scoring:
        mismatches.append("scoring_protocol_identity")
    if handoff.threshold_protocol_identities != expected_thresholds:
        mismatches.append("threshold_protocol_identities")
    if handoff.evaluation_protocol_identity != expected_evaluation:
        mismatches.append("evaluation_protocol_identity")
    if handoff.confirmatory_inference_protocol_identity != expected_inference:
        mismatches.append("confirmatory_inference_protocol_identity")
    if handoff.anchor_protocol_checksum != canonical_checksum(ANCHOR_DECISION_PROTOCOL):
        mismatches.append("anchor_protocol_checksum")
    if mismatches:
        raise AnchorReproductionError(
            "anchor confirmatory handoff is stale relative to the locked confirmatory programme",
            reason=",".join(mismatches),
        )
    return handoff


def _load_gate_decision_and_checksum(diagnostics_directory: Path) -> tuple[AnchorGateDecision, Checksum]:
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
    except (ValidationError, ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            "anchor-gate decision artifact is corrupted or schema-invalid",
            reason=str(gate_path),
        ) from error
    artifact_checksum = checksum_text(canonical_json_text(decision))
    marker_path = diagnostics_directory / AnchorArtifactFileName.GATE_COMPLETION.value
    if not marker_path.is_file():
        raise AnchorReproductionError(
            "anchor-gate completion marker is missing",
            reason=str(marker_path),
        )
    try:
        marker = AnchorGateCompletionMarker.model_validate_json(marker_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError, TypeError, OSError) as error:
        raise AnchorReproductionError(
            "anchor-gate completion marker is corrupted or schema-invalid",
            reason=str(marker_path),
        ) from error
    if marker.artifact_checksum != artifact_checksum or marker.status is not decision.status:
        raise AnchorReproductionError(
            "anchor-gate completion marker is stale or mismatched",
            reason=str(marker_path),
        )
    return decision, artifact_checksum


def _handoff_creation_identity(handoff: AnchorConfirmatoryHandoff) -> Checksum:
    payload = {name: getattr(handoff, name) for name in type(handoff).model_fields if name != "creation_identity"}
    return canonical_checksum(payload)


def _checkpoint_protocol_identity() -> Checksum:
    return canonical_checksum(
        {
            "checkpoint_protocol": CHECKPOINT_PROTOCOL,
            "selection_rule": CHECKPOINT_SELECTION_RULE,
        }
    )


def _scoring_protocol_identity() -> Checksum:
    return canonical_checksum(
        {
            "score_column": ScoreFrameColumn.RECONSTRUCTION_ERROR,
            "autoencoder": NBAIOT_AUTOENCODER,
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
