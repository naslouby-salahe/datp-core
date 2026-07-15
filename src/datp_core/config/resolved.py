from dataclasses import dataclass
from typing import assert_never

from datp_core.domain.artifacts.lineage import ResolvedConfigurationIdentity, ReuseImpact
from datp_core.domain.artifacts.references import ArtifactSchemaVersion
from datp_core.domain.experiments.protocols import ExecutionPolicy, ScientificProtocolField, ScientificProtocolSpec
from datp_core.domain.experiments.specification_changes import (
    EnvironmentChange,
    EnvironmentField,
    EnvironmentSpecification,
    ExecutionPolicyChange,
    ExecutionPolicyField,
    ScientificSpecificationChange,
    SpecificationChange,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedConfigurationArtifact:
    identity: ResolvedConfigurationIdentity
    schema_version: ArtifactSchemaVersion
    scientific: ScientificProtocolSpec
    execution: ExecutionPolicy
    environment: EnvironmentSpecification


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedSpecDiffRequest:
    previous: ResolvedConfigurationArtifact
    current: ResolvedConfigurationArtifact


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedSpecificationDiff:
    changes: tuple[SpecificationChange, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class _ScientificChangeRule:
    field: ScientificProtocolField
    reuse_impact: ReuseImpact


@dataclass(frozen=True, slots=True, kw_only=True)
class _ExecutionChangeRule:
    field: ExecutionPolicyField


SCIENTIFIC_CHANGE_RULES = (
    _ScientificChangeRule(field=ScientificProtocolField.TRACK, reuse_impact=ReuseImpact.TRAINING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.DATASET, reuse_impact=ReuseImpact.TRAINING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.PARTITIONING, reuse_impact=ReuseImpact.TRAINING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.SPLITS, reuse_impact=ReuseImpact.TRAINING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.PREPROCESSING, reuse_impact=ReuseImpact.TRAINING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.TRAINING, reuse_impact=ReuseImpact.TRAINING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.CHECKPOINTING, reuse_impact=ReuseImpact.SCORING_INVALIDATED),
    _ScientificChangeRule(
        field=ScientificProtocolField.CHECKPOINT_SELECTION, reuse_impact=ReuseImpact.SCORING_INVALIDATED
    ),
    _ScientificChangeRule(field=ScientificProtocolField.SCORING, reuse_impact=ReuseImpact.SCORING_INVALIDATED),
    _ScientificChangeRule(field=ScientificProtocolField.THRESHOLDS, reuse_impact=ReuseImpact.THRESHOLD_INVALIDATED),
    _ScientificChangeRule(
        field=ScientificProtocolField.EVALUATION,
        reuse_impact=ReuseImpact.EVALUATION_STATISTICS_INVALIDATED,
    ),
    _ScientificChangeRule(
        field=ScientificProtocolField.STATISTICS,
        reuse_impact=ReuseImpact.EVALUATION_STATISTICS_INVALIDATED,
    ),
    _ScientificChangeRule(
        field=ScientificProtocolField.RESOURCE_COSTS,
        reuse_impact=ReuseImpact.EVALUATION_STATISTICS_INVALIDATED,
    ),
)

EXECUTION_CHANGE_RULES = (
    _ExecutionChangeRule(field=ExecutionPolicyField.MODE),
    _ExecutionChangeRule(field=ExecutionPolicyField.DEVICE),
    _ExecutionChangeRule(field=ExecutionPolicyField.BUDGET),
    _ExecutionChangeRule(field=ExecutionPolicyField.PARALLELISM),
    _ExecutionChangeRule(field=ExecutionPolicyField.SEED_ROLES),
    _ExecutionChangeRule(field=ExecutionPolicyField.RESOURCE_PRESSURE),
    _ExecutionChangeRule(field=ExecutionPolicyField.RECOVERY),
)


class ResolvedSpecDiffer:
    @staticmethod
    def compare(request: ResolvedSpecDiffRequest) -> ResolvedSpecificationDiff:
        return ResolvedSpecificationDiff(
            changes=(
                *_scientific_changes(request.previous.scientific, request.current.scientific),
                *_execution_changes(request.previous.execution, request.current.execution),
                *_environment_changes(request.previous.environment, request.current.environment),
            )
        )


def _scientific_changes(
    previous: ScientificProtocolSpec,
    current: ScientificProtocolSpec,
) -> tuple[ScientificSpecificationChange, ...]:
    return tuple(
        _scientific_change(rule.field, rule.reuse_impact)
        for rule in SCIENTIFIC_CHANGE_RULES
        if getattr(previous, rule.field.value) != getattr(current, rule.field.value)
    )


def _scientific_change(field: ScientificProtocolField, reuse_impact: ReuseImpact) -> ScientificSpecificationChange:
    return ScientificSpecificationChange(
        field=field,
        affected_stages=(ScientificProtocolSpec.earliest_identity_stage_for(field),),
        reuse_impact=reuse_impact,
    )


def _execution_changes(previous: ExecutionPolicy, current: ExecutionPolicy) -> tuple[ExecutionPolicyChange, ...]:
    return tuple(
        _execution_change(rule.field)
        for rule in EXECUTION_CHANGE_RULES
        if getattr(previous, _execution_attribute(rule.field)) != getattr(current, _execution_attribute(rule.field))
    )


def _execution_change(field: ExecutionPolicyField) -> ExecutionPolicyChange:
    return ExecutionPolicyChange(
        field=field,
        affected_stages=(),
        reuse_impact=ReuseImpact.NO_OUTPUT_IMPACT,
    )


def _execution_attribute(field: ExecutionPolicyField) -> str:
    match field:
        case ExecutionPolicyField.MODE:
            return "execution_mode"
        case ExecutionPolicyField.DEVICE:
            return "device"
        case ExecutionPolicyField.BUDGET:
            return "budget"
        case ExecutionPolicyField.PARALLELISM:
            return "parallelism"
        case ExecutionPolicyField.SEED_ROLES:
            return "seed_roles"
        case ExecutionPolicyField.RESOURCE_PRESSURE:
            return "resource_pressure"
        case ExecutionPolicyField.RECOVERY:
            return "recovery"
        case _:
            assert_never(field)


def _environment_changes(
    previous: EnvironmentSpecification,
    current: EnvironmentSpecification,
) -> tuple[EnvironmentChange, ...]:
    if previous.storage_roots == current.storage_roots:
        return ()
    return (
        EnvironmentChange(
            field=EnvironmentField.STORAGE_ROOTS,
            affected_stages=(),
            reuse_impact=ReuseImpact.NO_OUTPUT_IMPACT,
        ),
    )
