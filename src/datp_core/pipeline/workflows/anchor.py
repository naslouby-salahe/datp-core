"""Historical anchor verification and programme-gate decision workflow."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.anchor.comparison import AnchorObservedMetric
from datp_core.anchor.gate import (
    AnchorGateDecision,
    AnchorGateStatus,
    assert_gate_not_bypassable,
    decide_anchor_gate,
    persist_anchor_gate_diagnostics,
)
from datp_core.anchor.reproduction import (
    AnchorDependencyBlocker,
    HistoricalMetricArtifactSource,
    independent_reproduction_dependency_blocker,
    load_historical_observations,
    reproduce_anchor,
)
from datp_core.domain.enums import ExperimentReadiness, StageOperationId
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values.base import NonNegativeIntegerValue
from datp_core.domain.values.checksums import Checksum
from datp_core.protocols.anchor import AnchorDecisionProtocol


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageRequest:
    protocol: AnchorDecisionProtocol
    observations: tuple[AnchorObservedMetric, ...] | None = None
    historical_sources: tuple[HistoricalMetricArtifactSource, ...] | None = None
    diagnostics_directory: Path | None = None
    request_independent_reproduction: bool = False


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageStatus:
    stage: ClassVar[StageOperationId] = StageOperationId.VERIFY_ANCHOR
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


def verify_anchor(request: VerifyAnchorStageRequest) -> VerifyAnchorStageResult:
    if request.request_independent_reproduction:
        raise AnchorReproductionError(
            "independent anchor re-execution requires federated training and scoring",
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
        raise AnchorReproductionError("supply either typed observations or historical sources, not both")
    if request.observations is not None:
        return request.observations, None
    if request.historical_sources is not None:
        return load_historical_observations(request.historical_sources), None
    return (), independent_reproduction_dependency_blocker()
