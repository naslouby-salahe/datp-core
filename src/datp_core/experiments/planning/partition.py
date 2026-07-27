"""Partition contract resolution."""

from __future__ import annotations

from typing import SupportsInt, cast

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.core.numbers import PositiveInt
from datp_core.data.contracts.materialization import PartitionSeedContract
from datp_core.experiments.catalogue.sweeps import ConditionSweepRecord, SweepConditionRecord


def resolve_partition_contract(
    config: ResolvedProjectConfiguration, experiment_id: ExperimentId, condition_name: str | None
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
        digest_bytes = PositiveInt(int(cast("SupportsInt", config.protocol_determinism.derived_seed_algorithm["digest_bytes"])))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Protocol determinism lacks a valid partition seed namespace") from exc
    return (matches[0], PartitionSeedContract(key=namespace.key, digest_bytes=digest_bytes))
