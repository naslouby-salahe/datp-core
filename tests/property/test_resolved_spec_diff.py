from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st

from datp_core.config.mapping.scientific import map_experiment_schema
from datp_core.config.resolved import (
    ResolvedConfigurationArtifact,
    ResolvedSpecDiffer,
    ResolvedSpecDiffRequest,
)
from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.artifacts.lineage import ResolvedConfigurationIdentity, ReuseImpact
from datp_core.domain.artifacts.references import ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.experiments.specification_changes import EnvironmentSpecification, StorageRootDescriptor
from datp_core.domain.runtime.policies import ExecutionMode
from datp_core.domain.thresholding.policies import ThresholdPercentile, ThresholdSuiteSpec
from tests.unit.config.test_mapping import experiment_config


def _resolved_configuration() -> ResolvedConfigurationArtifact:
    specification = map_experiment_schema(experiment_config())
    return ResolvedConfigurationArtifact(
        identity=ResolvedConfigurationIdentity(value=StageFingerprint(value="a" * 64)),
        schema_version=ArtifactSchemaVersion(value="v1"),
        scientific=specification.scientific_protocol,
        execution=specification.execution_policy,
        environment=EnvironmentSpecification(
            storage_roots=(StorageRootDescriptor(kind=StorageRootKind.SCORES, descriptor="machine-one"),)
        ),
    )


def _with_changes(
    configuration: ResolvedConfigurationArtifact,
    change_kinds: list[str],
) -> ResolvedConfigurationArtifact:
    changed = configuration
    if "threshold" in change_kinds:
        original = changed.scientific.thresholds.constructions[0]
        changed_thresholds = ThresholdSuiteSpec(
            constructions=(
                replace(original, percentile=ThresholdPercentile(value="0.90")),
                *changed.scientific.thresholds.constructions[1:],
            )
        )
        changed = replace(changed, scientific=replace(changed.scientific, thresholds=changed_thresholds))
    if "execution" in change_kinds:
        changed = replace(changed, execution=replace(changed.execution, execution_mode=ExecutionMode.SMOKE))
    if "environment" in change_kinds:
        changed = replace(
            changed,
            environment=EnvironmentSpecification(
                storage_roots=(StorageRootDescriptor(kind=StorageRootKind.SCORES, descriptor="machine-two"),)
            ),
        )
    return changed


@given(st.lists(st.sampled_from(("threshold", "execution", "environment")), min_size=1, unique=True))
def test_resolved_spec_diff_is_repeatable_and_direction_independent(change_kinds: list[str]) -> None:
    previous = _resolved_configuration()
    current = _with_changes(previous, change_kinds)

    forward = ResolvedSpecDiffer.compare(ResolvedSpecDiffRequest(previous=previous, current=current))
    repeated = ResolvedSpecDiffer.compare(ResolvedSpecDiffRequest(previous=previous, current=current))
    reverse = ResolvedSpecDiffer.compare(ResolvedSpecDiffRequest(previous=current, current=previous))

    assert repeated == forward
    assert {(type(change), change.field, change.reuse_impact) for change in forward.changes} == {
        (type(change), change.field, change.reuse_impact) for change in reverse.changes
    }
    assert {change.reuse_impact for change in forward.changes} <= {
        ReuseImpact.THRESHOLD_INVALIDATED,
        ReuseImpact.NO_OUTPUT_IMPACT,
    }
