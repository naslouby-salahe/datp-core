"""Stage: verify historical five-seed anchor and emit the programme gate decision."""

from dataclasses import dataclass, field
from enum import Enum
from json import dumps
from pathlib import Path
from typing import ClassVar

from datp_core.anchor.gate import assert_gate_not_bypassable, decide_anchor_gate
from datp_core.anchor.models import (
    AnchorArtifactFileName,
    AnchorDependencyBlocker,
    AnchorDiscrepancy,
    AnchorGateDecision,
    AnchorGateStatus,
    AnchorMetricComparison,
    AnchorObservedMetric,
    AnchorReproductionResult,
    HistoricalMetricArtifactSource,
)
from datp_core.anchor.reproduction import (
    independent_reproduction_dependency_blocker,
    load_historical_observations,
    reproduce_anchor,
)
from datp_core.domain.enums import ExperimentReadiness, StageOperationId
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Checksum, MetricValue, NonNegativeIntegerValue, checksum_text
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from datp_core.protocols.models import AnchorDecisionProtocol, SeedCohort

type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class CollectionCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "collection count"


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageRequest:
    protocol: AnchorDecisionProtocol = field(default=ANCHOR_DECISION_PROTOCOL)
    observations: tuple[AnchorObservedMetric, ...] | None = None
    historical_sources: tuple[HistoricalMetricArtifactSource, ...] | None = None
    diagnostics_directory: Path | None = None
    request_independent_reproduction: bool = False


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageStatus:
    stage: StageOperationId
    gate_status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    discrepancy_count: CollectionCount
    observation_count: CollectionCount
    reference_count: CollectionCount
    dependency_blocker: str | None
    diagnostics_checksum: Checksum


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageResult:
    status: VerifyAnchorStageStatus
    gate: AnchorGateDecision


def verify_anchor_stage(request: VerifyAnchorStageRequest | None = None) -> VerifyAnchorStageResult:
    """Validate the historical cohort, compare observations, and lock the programme gate.

    Independent re-training is Phase 08. When neither observations nor historical
    sources are supplied, the stage records a typed dependency blocker rather than
    executing federated training.
    """
    resolved = VerifyAnchorStageRequest() if request is None else request
    if resolved.request_independent_reproduction:
        raise AnchorReproductionError(
            "independent anchor re-execution requires Phase 08 training and scoring",
            subject=StageOperationId.VERIFY_ANCHOR,
            reason="dependency_blocker",
        )

    observations, dependency_blocker = _resolve_observations(resolved)
    reproduction = reproduce_anchor(
        protocol=resolved.protocol,
        observations=observations,
        dependency_blocker=dependency_blocker,
    )
    decision = assert_gate_not_bypassable(decide_anchor_gate(reproduction))
    diagnostics_checksum = _persist_diagnostics(decision, resolved.diagnostics_directory)
    blocker_detail = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    status = VerifyAnchorStageStatus(
        stage=StageOperationId.VERIFY_ANCHOR,
        gate_status=decision.status,
        dependent_readiness=decision.dependent_readiness,
        discrepancy_count=CollectionCount(len(decision.reproduction.discrepancies)),
        observation_count=CollectionCount(len(decision.reproduction.observations)),
        reference_count=CollectionCount(len(decision.reproduction.references)),
        dependency_blocker=blocker_detail,
        diagnostics_checksum=diagnostics_checksum,
    )
    return VerifyAnchorStageResult(status=status, gate=decision)


def _resolve_observations(
    request: VerifyAnchorStageRequest,
) -> tuple[tuple[AnchorObservedMetric, ...], AnchorDependencyBlocker | None]:
    if request.observations is not None and request.historical_sources is not None:
        raise AnchorReproductionError(
            "supply either typed observations or historical sources, not both",
            subject=StageOperationId.VERIFY_ANCHOR,
        )
    if request.observations is not None:
        return request.observations, None
    if request.historical_sources is not None:
        return load_historical_observations(request.historical_sources), None
    return (), independent_reproduction_dependency_blocker()


def _persist_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> Checksum:
    payload = _encode_json(_gate_decision_document(decision))
    checksum = checksum_text(payload)
    if diagnostics_directory is None:
        return checksum
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    (diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value).write_text(payload, encoding="utf-8")
    (diagnostics_directory / AnchorArtifactFileName.DISCREPANCIES.value).write_text(
        _encode_json([_discrepancy_document(item) for item in decision.reproduction.discrepancies]),
        encoding="utf-8",
    )
    return checksum


def _encode_json(document: JsonValue) -> str:
    return dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _gate_decision_document(decision: AnchorGateDecision) -> dict[str, JsonValue]:
    return {
        "status": decision.status.value,
        "dependent_readiness": decision.dependent_readiness.value,
        "blocking_discrepancies": [_discrepancy_document(item) for item in decision.blocking_discrepancies],
        "declared_discrepancies": [_discrepancy_document(item) for item in decision.declared_discrepancies],
        "reproduction": _reproduction_document(decision.reproduction),
    }


def _reproduction_document(reproduction: AnchorReproductionResult) -> dict[str, JsonValue]:
    return {
        "experiment": reproduction.experiment.value,
        "evidence_role": reproduction.evidence_role.value,
        "seed_cohort": _seed_cohort_document(reproduction.seed_cohort),
        "reference_count": len(reproduction.references),
        "observation_count": len(reproduction.observations),
        "seed_subset": {
            "expected_seeds": [seed.value for seed in reproduction.seed_subset_comparison.expected_seeds],
            "observed_seeds": [seed.value for seed in reproduction.seed_subset_comparison.observed_seeds],
            "decision": reproduction.seed_subset_comparison.decision.value,
            "reason": _optional_enum(reproduction.seed_subset_comparison.reason),
        },
        "metric_comparisons": [_comparison_document(item) for item in reproduction.metric_comparisons],
        "discrepancies": [_discrepancy_document(item) for item in reproduction.discrepancies],
        "dependency_blocker": (
            None
            if reproduction.dependency_blocker is None
            else {
                "kind": reproduction.dependency_blocker.kind.value,
                "detail": reproduction.dependency_blocker.detail,
            }
        ),
    }


def _seed_cohort_document(cohort: SeedCohort) -> dict[str, JsonValue]:
    return {"values": [seed.value for seed in cohort.values]}


def _comparison_document(comparison: AnchorMetricComparison) -> dict[str, JsonValue]:
    return {
        "seed": comparison.reference.seed.value,
        "threshold_method": comparison.reference.threshold_method.value,
        "metric": comparison.reference.metric.value,
        "expected": _metric_json(comparison.reference.value),
        "observed": None if comparison.observation is None else _metric_json(comparison.observation.value),
        "decision": comparison.decision.value,
        "signed_difference": comparison.signed_difference,
        "relative_difference": comparison.relative_difference,
        "tolerance_strategy": comparison.tolerance_rule.strategy.value,
        "reason": _optional_enum(comparison.reason),
    }


def _discrepancy_document(discrepancy: AnchorDiscrepancy) -> dict[str, JsonValue]:
    return {
        "reason": discrepancy.reason.value,
        "seed": None if discrepancy.seed is None else discrepancy.seed.value,
        "threshold_method": None if discrepancy.threshold_method is None else discrepancy.threshold_method.value,
        "metric": None if discrepancy.metric is None else discrepancy.metric.value,
        "expected_value": _optional_metric(discrepancy.expected_value),
        "observed_value": _optional_metric(discrepancy.observed_value),
        "signed_difference": discrepancy.signed_difference,
        "relative_difference": discrepancy.relative_difference,
        "tolerance_strategy": (
            None if discrepancy.tolerance_rule is None else discrepancy.tolerance_rule.strategy.value
        ),
        "artifact_path": None if discrepancy.artifact_path is None else discrepancy.artifact_path.as_posix(),
        "artifact_checksum": None if discrepancy.artifact_checksum is None else discrepancy.artifact_checksum.value,
        "detail": discrepancy.detail,
    }


def _metric_json(value: MetricValue) -> float:
    return value.value


def _optional_metric(value: MetricValue | None) -> float | None:
    return None if value is None else value.value


def _optional_enum(value: Enum | None) -> str | None:
    return None if value is None else value.value
