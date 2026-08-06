"""Historical anchor verification and programme-gate decision workflow."""

from datp_core.anchor.gate import (
    assert_gate_not_bypassable,
    decide_anchor_gate,
    persist_anchor_gate_diagnostics,
)
from datp_core.anchor.models import (
    AnchorDependencyBlocker,
    AnchorObservedMetric,
    VerifyAnchorStageRequest,
    VerifyAnchorStageResult,
    VerifyAnchorStageStatus,
)
from datp_core.anchor.reproduction import (
    independent_reproduction_dependency_blocker,
    load_historical_observations,
    reproduce_anchor,
)
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values.base import NonNegativeIntegerValue


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
