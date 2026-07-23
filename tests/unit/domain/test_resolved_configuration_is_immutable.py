"""Deep immutability of the resolved configuration graph.

Mutation must be impossible at multiple nesting depths: the top-level container, a nested
dataset record, a nested training-profile record, a tuple-valued field, and a Mapping-valued
field. This is required after fingerprint computation -- the resolved graph is the single
scientific/execution identity authority and must never silently change underneath it.
"""

from __future__ import annotations

import operator
from collections.abc import MutableSequence
from typing import cast

import pytest
from attrs.exceptions import FrozenInstanceError

from datp_core.configuration.project import resolve_project_configuration
from datp_core.pipeline.identifiers import DatasetId, TrainingProfileId


@pytest.fixture(scope="module")
def resolved_config():
    return resolve_project_configuration()


def test_top_level_resolved_configuration_is_frozen(resolved_config) -> None:
    with pytest.raises(FrozenInstanceError):
        resolved_config.scientific_fingerprint = resolved_config.scientific_fingerprint


def test_nested_dataset_record_is_frozen(resolved_config) -> None:
    dataset = resolved_config.datasets.get(DatasetId("nbaiot"))
    with pytest.raises(FrozenInstanceError):
        dataset.display_name = dataset.display_name


def test_nested_dataset_paths_record_is_frozen(resolved_config) -> None:
    dataset = resolved_config.datasets.get(DatasetId("nbaiot"))
    with pytest.raises(FrozenInstanceError):
        dataset.paths.raw_root = dataset.paths.raw_root


def test_nested_training_profile_record_is_frozen(resolved_config) -> None:
    training_profile_id = next(iter(resolved_config.training_profiles))
    training = resolved_config.training_profiles.get(training_profile_id)
    with pytest.raises(FrozenInstanceError):
        training.model_architecture_id = training.model_architecture_id


def test_a_deeply_nested_materialization_record_is_frozen(resolved_config) -> None:
    dataset = resolved_config.datasets.get(DatasetId("nbaiot"))
    materialization = dataset.materializations[0]
    with pytest.raises(FrozenInstanceError):
        materialization.normalization_strategy = materialization.normalization_strategy


def test_tuple_valued_fields_reject_item_assignment(resolved_config) -> None:
    dataset = resolved_config.datasets.get(DatasetId("nbaiot"))
    assert isinstance(dataset.materializations, tuple)
    replacement = dataset.materializations[0]
    mutable_view = cast(MutableSequence, dataset.materializations)
    with pytest.raises(TypeError):
        operator.setitem(mutable_view, 0, replacement)


def test_mapping_valued_field_rejects_item_assignment(resolved_config) -> None:
    dataset = resolved_config.datasets.get(DatasetId("nbaiot"))
    row_exclusion = dataset.materializations[0].row_exclusion
    assert len(row_exclusion) > 0

    with pytest.raises(TypeError):
        operator.setitem(row_exclusion, "a_new_key", "a_new_value")


def test_mapping_valued_field_rejects_item_deletion(resolved_config) -> None:
    dataset = resolved_config.datasets.get(DatasetId("nbaiot"))
    row_exclusion = dataset.materializations[0].row_exclusion
    assert len(row_exclusion) > 0
    existing_key = next(iter(row_exclusion))

    with pytest.raises(TypeError):
        operator.delitem(row_exclusion, existing_key)


def test_typed_domain_registry_exposes_no_public_mutation_method() -> None:
    resolved_config_local = resolve_project_configuration()
    registry = resolved_config_local.model_architectures
    assert not hasattr(registry, "__setitem__")
    assert not hasattr(registry, "__delitem__")
    assert not hasattr(registry, "clear")
    assert not hasattr(registry, "pop")
    assert not hasattr(registry, "update")


def test_threshold_policy_record_is_frozen_at_the_union_variant_level(resolved_config) -> None:
    policy_id = next(iter(resolved_config.threshold_policies))
    policy = resolved_config.threshold_policies.get(policy_id)
    with pytest.raises(FrozenInstanceError):
        policy.quantile = policy.quantile


def test_experiment_record_prerequisite_and_evaluation_tuples_are_immutable(resolved_config) -> None:
    experiment_id = next(iter(resolved_config.experiments))
    experiment = resolved_config.experiments.get(experiment_id)
    assert isinstance(experiment.prerequisites, tuple)
    assert isinstance(experiment.evaluations, tuple)
    with pytest.raises(FrozenInstanceError):
        experiment.display_name = experiment.display_name


def test_second_resolution_produces_an_independently_frozen_graph_without_shared_mutable_state(
    resolved_config,
) -> None:
    """Guards against accidental module-level mutable caching between resolutions."""
    other = resolve_project_configuration()
    dataset_a = resolved_config.datasets.get(DatasetId("nbaiot"))
    dataset_b = other.datasets.get(DatasetId("nbaiot"))
    assert dataset_a is not dataset_b
    assert dataset_a == dataset_b


def test_unknown_training_profile_id_raises_key_error_not_none(resolved_config) -> None:
    with pytest.raises(KeyError):
        resolved_config.training_profiles.get(TrainingProfileId("definitely_not_a_registered_profile"))
