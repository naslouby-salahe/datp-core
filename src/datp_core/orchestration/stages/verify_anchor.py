"""Stage: verify historical five-seed anchor and emit the programme gate decision."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.anchor.gate import assert_gate_not_bypassable, decide_anchor_gate, persist_anchor_gate_diagnostics
from datp_core.anchor.models import (
    AnchorDependencyBlocker,
    AnchorGateDecision,
    AnchorGateStatus,
    AnchorObservedMetric,
    HistoricalMetricArtifactSource,
)
from datp_core.anchor.reproduction import (
    independent_reproduction_dependency_blocker,
    load_historical_observations,
    reproduce_anchor,
)
from datp_core.domain.enums import ExperimentReadiness, StageOperationId
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Checksum, NonNegativeIntegerValue
from datp_core.protocols.models import AnchorDecisionProtocol


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageRequest:
    protocol: AnchorDecisionProtocol
    observations: tuple[AnchorObservedMetric, ...] | None = None
    historical_sources: tuple[HistoricalMetricArtifactSource, ...] | None = None
    diagnostics_directory: Path | None = None
    request_independent_reproduction: bool = False


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageStatus:
    stage: StageOperationId
    gate_status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    discrepancy_count: NonNegativeIntegerValue
    observation_count: NonNegativeIntegerValue
    reference_count: NonNegativeIntegerValue
    dependency_blocker: str | None
    diagnostics_checksum: Checksum


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageResult:
    status: VerifyAnchorStageStatus
    gate: AnchorGateDecision


def verify_anchor_stage(request: VerifyAnchorStageRequest) -> VerifyAnchorStageResult:
    """Validate the historical cohort, compare observations, and lock the programme gate.

    When neither observations nor historical sources are supplied, the stage records
    a typed dependency blocker rather than executing federated training.
    """
    if request.request_independent_reproduction:
        raise AnchorReproductionError(
            "independent anchor re-execution requires federated training and scoring",
            subject=StageOperationId.VERIFY_ANCHOR,
            reason="dependency_blocker",
        )

    observations, dependency_blocker = _resolve_observations(request)
    reproduction = reproduce_anchor(
        protocol=request.protocol,
        observations=observations,
        dependency_blocker=dependency_blocker,
    )
    decision = assert_gate_not_bypassable(decide_anchor_gate(reproduction))
    diagnostics_checksum = persist_anchor_gate_diagnostics(decision, request.diagnostics_directory)
    blocker_detail = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    status = VerifyAnchorStageStatus(
        stage=StageOperationId.VERIFY_ANCHOR,
        gate_status=decision.status,
        dependent_readiness=decision.dependent_readiness,
        discrepancy_count=NonNegativeIntegerValue(len(decision.reproduction.discrepancies)),
        observation_count=NonNegativeIntegerValue(len(decision.reproduction.observations)),
        reference_count=NonNegativeIntegerValue(len(decision.reproduction.references)),
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
