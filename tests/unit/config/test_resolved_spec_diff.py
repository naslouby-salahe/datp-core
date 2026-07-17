from dataclasses import fields, replace

from datp_core.config.mapping.scientific import map_experiment_schema
from datp_core.config.resolved import (
    EXECUTION_CHANGE_RULES,
    SCIENTIFIC_CHANGE_RULES,
    ResolvedConfigurationArtifact,
    ResolvedSpecDiffer,
    ResolvedSpecDiffRequest,
)
from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.artifacts.lineage import ResolvedConfigurationIdentity, ReuseImpact
from datp_core.domain.artifacts.references import ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.experiments.protocols import ExecutionPolicy, ScientificProtocolField
from datp_core.domain.experiments.specification_changes import (
    EnvironmentChange,
    EnvironmentSpecification,
    ExecutionPolicyField,
    ScientificSpecificationChange,
    StorageRootDescriptor,
)
from datp_core.domain.runtime.policies import PipelineStage
from datp_core.domain.thresholding.policies import ThresholdPercentile, ThresholdSuiteSpec
from tests.support.composed_configuration import composed_profile_catalogue
from tests.unit.config.test_mapping import experiment_config


def _resolved_configuration(*, descriptor: str = "machine-one") -> ResolvedConfigurationArtifact:
    specification = map_experiment_schema(experiment_config(), catalogue=composed_profile_catalogue())
    return ResolvedConfigurationArtifact(
        identity=ResolvedConfigurationIdentity(value=StageFingerprint(value="a" * 64)),
        schema_version=ArtifactSchemaVersion(value="v1"),
        scientific=specification.scientific_protocol,
        execution=specification.execution_policy,
        environment=EnvironmentSpecification(
            storage_roots=(StorageRootDescriptor(kind=StorageRootKind.SCORES, descriptor=descriptor),)
        ),
    )


def _with_threshold_change(configuration: ResolvedConfigurationArtifact) -> ResolvedConfigurationArtifact:
    arm = configuration.scientific.evaluation_arm
    original = arm.thresholds.constructions[0]
    changed_thresholds = ThresholdSuiteSpec(
        constructions=(
            replace(original, percentile=ThresholdPercentile(value="0.90")),
            *arm.thresholds.constructions[1:],
        )
    )
    return replace(
        configuration,
        scientific=replace(
            configuration.scientific,
            evaluation_arm=replace(arm, thresholds=changed_thresholds),
        ),
    )


def test_threshold_only_change_invalidates_threshold_artifacts() -> None:
    previous = _resolved_configuration()
    current = _with_threshold_change(previous)

    result = ResolvedSpecDiffer.compare(ResolvedSpecDiffRequest(previous=previous, current=current))

    assert len(result.changes) == 1
    assert type(result.changes[0]) is ScientificSpecificationChange
    assert result.changes[0].affected_stages == (PipelineStage.THRESHOLD,)
    assert result.changes[0].reuse_impact is ReuseImpact.THRESHOLD_INVALIDATED


def test_machine_descriptor_change_has_no_output_impact() -> None:
    previous = _resolved_configuration(descriptor="machine-one")
    current = _resolved_configuration(descriptor="machine-two")

    result = ResolvedSpecDiffer.compare(ResolvedSpecDiffRequest(previous=previous, current=current))

    assert len(result.changes) == 1
    assert type(result.changes[0]) is EnvironmentChange
    assert result.changes[0].reuse_impact is ReuseImpact.NO_OUTPUT_IMPACT


def test_compare_never_mutates_either_resolved_configuration() -> None:
    previous = _resolved_configuration()
    current = _with_threshold_change(previous)
    before = (previous, current)

    ResolvedSpecDiffer.compare(ResolvedSpecDiffRequest(previous=previous, current=current))

    assert before == (previous, current)


def test_every_resolved_specification_field_has_a_closed_diff_classification() -> None:
    assert tuple(rule.field for rule in SCIENTIFIC_CHANGE_RULES) == tuple(ScientificProtocolField)
    protocol = _resolved_configuration().scientific
    assert {rule.field for rule in SCIENTIFIC_CHANGE_RULES} == {input_.field for input_ in protocol.identity_inputs()}
    assert tuple(field.name for field in fields(ExecutionPolicy)) == (
        "execution_mode",
        "device",
        "budget",
        "parallelism",
        "seed_roles",
        "resource_pressure",
        "recovery",
    )
    assert tuple(ExecutionPolicyField) == (
        ExecutionPolicyField.MODE,
        ExecutionPolicyField.DEVICE,
        ExecutionPolicyField.BUDGET,
        ExecutionPolicyField.PARALLELISM,
        ExecutionPolicyField.SEED_ROLES,
        ExecutionPolicyField.RESOURCE_PRESSURE,
        ExecutionPolicyField.RECOVERY,
    )
    assert tuple(rule.field for rule in EXECUTION_CHANGE_RULES) == tuple(ExecutionPolicyField)
