"""Dagster partitions derived from the single resolved project configuration."""

from __future__ import annotations

from dagster import StaticPartitionsDefinition

from datp_core.config.resolver import ResolvedProjectConfiguration


def experiment_partitions(config: ResolvedProjectConfiguration) -> StaticPartitionsDefinition:
    """Build stable experiment partitions from authored experiment identifiers."""
    return StaticPartitionsDefinition(sorted(identifier.value for identifier in config.experiments.keys()))


def seed_partitions(config: ResolvedProjectConfiguration) -> StaticPartitionsDefinition:
    """Build stable seed partitions from every resolved seed cohort."""
    seeds = sorted({str(seed.value) for cohort in config.seed_cohorts.values() for seed in cohort.training_seeds})
    return StaticPartitionsDefinition(seeds)
