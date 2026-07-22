"""Shared stage-handler protocol and cross-cutting helpers used by every feature-owned stage."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from time import time
from typing import Protocol

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactParent,
    ArtifactRepository,
    BytesPayload,
    FilePayload,
)
from datp_core.domain.catalogue import (
    ConditionSweepRecord,
    EligibilityGateRecord,
    SweepConditionRecord,
)
from datp_core.domain.datasets import PartitionSeedContract
from datp_core.domain.identifiers import ExperimentId, RunId
from datp_core.domain.outcomes import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.domain.splits import SplitManifest
from datp_core.domain.statistics import holm_adjust_p_values
from datp_core.domain.values import PositiveInt, Seed


class StageHandler(Protocol):
    """One executable stage that may only report success after an artifact commit."""

    stage: StageKind

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome: ...


def commit_artifact(
    repository: ArtifactRepository,
    config: ResolvedProjectConfiguration,
    context: StageJobContext,
    *,
    artifact_key: ArtifactKey,
    artifact_format: ArtifactFormat,
    relative_path: str,
    parents: tuple[ArtifactParent, ...],
    payload: BytesPayload | FilePayload,
):
    return repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=artifact_format,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=parents,
                schema_version=1,
                creation_timestamp=time(),
                environment_identity=config.runtime.bootstrap.environment_identity,
                experiment_id=context.experiment_id,
                seed=Seed(context.seed) if context.seed is not None else None,
            ),
            payload=payload,
        )
    )


def artifact_parents(config: ResolvedProjectConfiguration, artifacts: tuple[ArtifactKey, ...]) -> tuple[ArtifactParent, ...]:
    return tuple(
        ArtifactParent(parent_key=artifact, scientific_fingerprint=config.scientific_fingerprint)
        for artifact in artifacts
    )


def git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def apply_holm_correction(results: list[dict[str, object]]) -> None:
    paired_indices = [
        i
        for i, record in enumerate(results)
        if record.get("analysis_label") and "p_value" in record and record.get("p_value") is not None
    ]
    if len(paired_indices) < 2:
        return
    p_values = tuple(float(results[i]["p_value"]) for i in paired_indices)  # type: ignore[arg-type]
    adjusted = holm_adjust_p_values(p_values)
    for idx, adj_p in zip(paired_indices, adjusted, strict=True):
        results[idx]["holm_adjusted_p_value"] = adj_p


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


def resolve_partition_contract(
    config: ResolvedProjectConfiguration, experiment_id, condition_name: str | None
) -> tuple[SweepConditionRecord | None, PartitionSeedContract | None]:
    if condition_name is None:
        return (None, None)
    experiment = config.experiments.get(experiment_id)
    matches = tuple(
        condition
        for sweep in experiment.sweeps
        if isinstance(sweep, ConditionSweepRecord)
        for condition in sweep.conditions
        if condition.name == condition_name
    )
    if len(matches) != 1:
        raise ValueError(f"Experiment '{experiment_id.value}' has no unique partition condition '{condition_name}'")
    try:
        namespace = config.protocol_determinism.seed_namespaces["partition"]
        digest_bytes = PositiveInt(int(config.protocol_determinism.derived_seed_algorithm["digest_bytes"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Protocol determinism lacks a valid partition seed namespace") from exc
    return (matches[0], PartitionSeedContract(key=namespace.key, digest_bytes=digest_bytes))
