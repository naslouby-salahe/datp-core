"""Resolved execution-profile record tests."""

from pathlib import Path

import pytest

from datp_core.config.runtime_settings import (
    DeterminismStrictRecord,
    DevicePolicyRecord,
    ExecutionProfileRecord,
    RawSourcePolicyRecord,
    ResourcePressureRecord,
    RuntimeBootstrapSettings,
    resolve_runtime_configuration,
)
from datp_core.config.yaml_loader import YamlConfigurationReader


def _authored():
    return YamlConfigurationReader.read_runtime_document(Path("configs/runtime.yaml"))


def test_execution_profiles_resolve_to_pure_records() -> None:
    runtime = resolve_runtime_configuration(authored_runtime=_authored())
    profiles = runtime.execution_profiles
    assert set(profiles) == {"scientific", "development", "smoke", "dataset_audit", "test_smoke"}
    assert all(isinstance(p, ExecutionProfileRecord) for p in profiles.values())

    scientific = profiles["scientific"]
    assert scientific.device_policy == "cuda_required"
    assert scientific.determinism == "strict"
    assert scientific.data_loading["chunk_row_count"] == 50000
    assert scientific.data_loading["streaming"] is True
    assert scientific.log_interval_rounds.value == 25
    assert scientific.atomic_write is True

    audit = profiles["dataset_audit"]
    assert audit.device_policy == "cpu_only"
    assert audit.temporary_storage_cleanup == "remove_on_success_and_on_failure"


def test_runtime_policies_resolve_to_pure_records() -> None:
    runtime = resolve_runtime_configuration(authored_runtime=_authored())

    assert isinstance(runtime.raw_source_policy, RawSourcePolicyRecord)
    assert runtime.raw_source_policy.write_access == "forbidden"
    assert runtime.raw_source_policy.create_files_under_raw_root == "forbidden"

    assert isinstance(runtime.determinism_enforcement, DeterminismStrictRecord)
    assert runtime.determinism_enforcement.python_hash_seed == 0
    assert runtime.determinism_enforcement.torch_use_deterministic_algorithms is True
    assert runtime.determinism_enforcement.cudnn_benchmark is False
    assert "gpu_identity" in runtime.determinism_enforcement.recorded_environment_fields

    assert isinstance(runtime.device_policy_rules, DevicePolicyRecord)
    assert runtime.device_policy_rules.cuda_required["cpu_fallback"] == "forbidden"
    assert runtime.device_policy_rules.cpu_only["permitted_for_scientific_training_or_scoring"] is False

    assert isinstance(runtime.resource_pressure_policy, ResourcePressureRecord)
    assert runtime.resource_pressure_policy.on_budget_exceeded == "block_execution_and_report"


def test_active_execution_profile_defaults_to_scientific() -> None:
    runtime = resolve_runtime_configuration(authored_runtime=_authored())
    assert runtime.active_execution_profile is runtime.execution_profiles["scientific"]
    assert runtime.active_execution_profile.identifier == "scientific"


def test_unknown_active_execution_profile_is_rejected() -> None:
    settings = RuntimeBootstrapSettings(execution_profile="does_not_exist")
    with pytest.raises(ValueError, match="Active execution profile"):
        resolve_runtime_configuration(authored_runtime=_authored(), bootstrap_settings=settings)
