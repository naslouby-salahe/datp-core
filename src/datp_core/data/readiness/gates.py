"""Typed readiness-gate evaluation."""

from __future__ import annotations

from datp_core.data.contracts.eligibility import ReadinessGate
from datp_core.data.contracts.enums import DatasetCapability, ReadinessGateFailureCode
from datp_core.data.manifests.summary import MaterializedSplitSummary
from datp_core.data.readiness.models import ReadinessGateFailure


def evaluate_readiness_gates(
    gates: tuple[ReadinessGate, ...],
    capabilities: tuple[DatasetCapability, ...],
    summary: MaterializedSplitSummary,
) -> tuple[ReadinessGateFailure, ...]:
    failures: list[ReadinessGateFailure] = []
    eligible_count = len(summary.eligible_client_ids)
    client_count = len(summary.client_ids)
    eligible_proportion = 0.0 if client_count == 0 else eligible_count / client_count
    for gate in gates:
        if eligible_count < int(gate.minimum_eligible_clients):
            failures.append(
                ReadinessGateFailure(
                    gate_id=gate.identifier.value,
                    code=ReadinessGateFailureCode.MINIMUM_ELIGIBLE_CLIENTS,
                    detail=f"observed {eligible_count}; requires {int(gate.minimum_eligible_clients)}",
                )
            )
        if eligible_proportion < float(gate.minimum_eligible_proportion):
            failures.append(
                ReadinessGateFailure(
                    gate_id=gate.identifier.value,
                    code=ReadinessGateFailureCode.MINIMUM_ELIGIBLE_PROPORTION,
                    detail=(
                        f"observed eligible proportion {eligible_proportion:.12g}; "
                        f"requires {float(gate.minimum_eligible_proportion):.12g}"
                    ),
                )
            )
        for capability in gate.required_capabilities:
            if capability not in capabilities:
                failures.append(
                    ReadinessGateFailure(
                        gate_id=gate.identifier.value,
                        code=ReadinessGateFailureCode.REQUIRED_CAPABILITY_MISSING,
                        detail=f"required capability '{capability.value}' is absent",
                    )
                )
    return tuple(failures)
