"""Stage: verify historical five-seed anchor and emit the programme gate decision."""

from dataclasses import dataclass, field
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
    AnchorSeedSubsetComparison,
    HistoricalMetricArtifactSource,
)
from datp_core.anchor.reproduction import (
    independent_reproduction_dependency_blocker,
    load_historical_observations,
    reproduce_anchor,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import ExperimentReadiness, StageOperationId
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Checksum, MetricValue, NonNegativeIntegerValue, checksum_text
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from datp_core.protocols.models import AnchorDecisionProtocol, SeedCohort


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


# Typed diagnostic-document boundary models. Every anchor gate diagnostic persisted to disk
# or checksummed is a StrictModel instance, never a raw dict, matching the codebase's
# typed-serialization-boundary convention (see artifacts/serialization.py).


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


def _persist_diagnostics(decision: AnchorGateDecision, diagnostics_directory: Path | None) -> Checksum:
    document = _gate_decision_document(decision)
    payload = document.model_dump_json()
    checksum = checksum_text(payload)
    if diagnostics_directory is None:
        return checksum
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    (diagnostics_directory / AnchorArtifactFileName.GATE_DECISION.value).write_text(payload, encoding="utf-8")
    discrepancies = tuple(_discrepancy_document(item) for item in decision.reproduction.discrepancies)
    (diagnostics_directory / AnchorArtifactFileName.DISCREPANCIES.value).write_text(
        _encode_discrepancies(discrepancies), encoding="utf-8"
    )
    return checksum


def _encode_discrepancies(discrepancies: tuple[DiscrepancyDocument, ...]) -> str:
    from json import dumps

    return dumps([item.model_dump(mode="json") for item in discrepancies], sort_keys=True, separators=(",", ":"))


def _gate_decision_document(decision: AnchorGateDecision) -> GateDecisionDocument:
    return GateDecisionDocument(
        status=decision.status.value,
        dependent_readiness=decision.dependent_readiness.value,
        blocking_discrepancies=tuple(_discrepancy_document(item) for item in decision.blocking_discrepancies),
        declared_discrepancies=tuple(_discrepancy_document(item) for item in decision.declared_discrepancies),
        reproduction=_reproduction_document(decision.reproduction),
    )


def _reproduction_document(reproduction: AnchorReproductionResult) -> ReproductionDocument:
    return ReproductionDocument(
        experiment=reproduction.experiment.value,
        evidence_role=reproduction.evidence_role.value,
        seed_cohort=_seed_cohort_values(reproduction.seed_cohort),
        reference_count=len(reproduction.references),
        observation_count=len(reproduction.observations),
        seed_subset=_seed_subset_document(reproduction.seed_subset_comparison),
        metric_comparisons=tuple(_comparison_document(item) for item in reproduction.metric_comparisons),
        discrepancies=tuple(_discrepancy_document(item) for item in reproduction.discrepancies),
        dependency_blocker=_dependency_blocker_document(reproduction.dependency_blocker),
    )


def _seed_cohort_values(cohort: SeedCohort) -> tuple[int, ...]:
    return tuple(seed.value for seed in cohort.values)


def _seed_subset_document(comparison: AnchorSeedSubsetComparison) -> SeedSubsetComparisonDocument:
    return SeedSubsetComparisonDocument(
        expected_seeds=tuple(seed.value for seed in comparison.expected_seeds),
        observed_seeds=tuple(seed.value for seed in comparison.observed_seeds),
        decision=comparison.decision.value,
        reason=_optional_enum_value(comparison.reason),
    )


def _dependency_blocker_document(blocker: AnchorDependencyBlocker | None) -> DependencyBlockerDocument | None:
    if blocker is None:
        return None
    return DependencyBlockerDocument(kind=blocker.kind.value, detail=blocker.detail)


def _comparison_document(comparison: AnchorMetricComparison) -> MetricComparisonDocument:
    return MetricComparisonDocument(
        seed=comparison.reference.seed.value,
        threshold_method=comparison.reference.threshold_method.value,
        metric=comparison.reference.metric.value,
        expected=_metric_value(comparison.reference.value),
        observed=_optional_metric_value(comparison.observation.value if comparison.observation is not None else None),
        decision=comparison.decision.value,
        signed_difference=comparison.signed_difference,
        relative_difference=comparison.relative_difference,
        tolerance_strategy=comparison.tolerance_rule.strategy.value,
        reason=_optional_enum_value(comparison.reason),
    )


def _discrepancy_document(discrepancy: AnchorDiscrepancy) -> DiscrepancyDocument:
    return DiscrepancyDocument(
        reason=discrepancy.reason.value,
        seed=None if discrepancy.seed is None else discrepancy.seed.value,
        threshold_method=_optional_enum_value(discrepancy.threshold_method),
        metric=_optional_enum_value(discrepancy.metric),
        expected_value=_optional_metric_value(discrepancy.expected_value),
        observed_value=_optional_metric_value(discrepancy.observed_value),
        signed_difference=discrepancy.signed_difference,
        relative_difference=discrepancy.relative_difference,
        tolerance_strategy=(None if discrepancy.tolerance_rule is None else discrepancy.tolerance_rule.strategy.value),
        artifact_path=None if discrepancy.artifact_path is None else discrepancy.artifact_path.as_posix(),
        artifact_checksum=None if discrepancy.artifact_checksum is None else discrepancy.artifact_checksum.value,
        detail=discrepancy.detail,
    )


def _metric_value(value: MetricValue) -> float:
    return value.value


def _optional_metric_value(value: MetricValue | None) -> float | None:
    return None if value is None else value.value


def _optional_enum_value(value) -> str | None:
    return None if value is None else value.value
