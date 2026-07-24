"""Eligibility/readiness gate evaluation."""

from __future__ import annotations

from collections.abc import Mapping

from datp_core.core.identifiers import ExperimentId
from datp_core.data.manifests.models import SplitManifest
from datp_core.experiments import EligibilityGateRecord


def evaluate_readiness_gates(
    gate_names: tuple[str, ...],
    gates: Mapping[str, EligibilityGateRecord],
    manifest: SplitManifest,
    experiment_id: ExperimentId,
) -> list[str]:
    issues: list[str] = []
    for gate_name in gate_names:
        gate = gates.get(gate_name)
        if gate is None:
            issues.append(f"unknown readiness gate: {gate_name}")
            continue
        if experiment_id not in gate.applies_to_experiments:
            continue
        candidate_count = len(manifest.client_ids)
        eligible_count = len(manifest.eligible_client_ids)
        if candidate_count == 0:
            issues.append(f"{gate_name}: no candidate clients in split manifest")
            continue
        proportion = eligible_count / candidate_count
        if proportion < float(gate.minimum_eligible_client_proportion):
            issues.append(
                f"{gate_name}: eligible proportion {proportion:.3f} below minimum "
                f"{float(gate.minimum_eligible_client_proportion)} "
                f"({eligible_count}/{candidate_count} clients eligible)"
            )
    return issues
