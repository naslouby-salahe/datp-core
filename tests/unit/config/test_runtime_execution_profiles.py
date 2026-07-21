"""Resolved execution-profile record tests."""

import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from datp_core.config.resolver import resolve_project_configuration
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
    assert scientific.data_loading.chunk_row_count.value == 50000
    assert scientific.data_loading.streaming is True
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


def test_explicit_active_execution_profile_selection_is_honored() -> None:
    settings = RuntimeBootstrapSettings(execution_profile="scientific")
    runtime = resolve_runtime_configuration(authored_runtime=_authored(), bootstrap_settings=settings)
    assert runtime.active_execution_profile is runtime.execution_profiles.get("scientific")
    assert runtime.active_execution_profile.identifier == "scientific"


def test_missing_active_execution_profile_selection_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATP_EXECUTION_PROFILE", raising=False)
    with pytest.raises(ValidationError):
        RuntimeBootstrapSettings()  # pyright: ignore[reportCallIssue]


def test_unknown_active_execution_profile_is_rejected() -> None:
    settings = RuntimeBootstrapSettings(execution_profile="does_not_exist")
    with pytest.raises(ValueError, match="Active execution profile"):
        resolve_runtime_configuration(authored_runtime=_authored(), bootstrap_settings=settings)


def _copy_real_config_tree(tmp_path: Path) -> Path:
    for name in ("runtime.yaml", "protocols.yaml", "experiments.yaml"):
        shutil.copy(f"configs/{name}", tmp_path / name)
    (tmp_path / "datasets").mkdir()
    for source in Path("configs/datasets").glob("*.yaml"):
        shutil.copy(source, tmp_path / "datasets" / source.name)
    return tmp_path


def test_changing_active_execution_profile_changes_execution_identity_only(tmp_path: Path) -> None:
    config_dir = _copy_real_config_tree(tmp_path)
    scientific_config = resolve_project_configuration(
        config_dir=config_dir,
        bootstrap_settings=RuntimeBootstrapSettings(execution_profile="scientific"),
    )
    development_config = resolve_project_configuration(
        config_dir=config_dir,
        bootstrap_settings=RuntimeBootstrapSettings(execution_profile="development"),
    )

    assert scientific_config.scientific_fingerprint == development_config.scientific_fingerprint
    assert scientific_config.execution_fingerprint != development_config.execution_fingerprint


def test_editing_an_inactive_execution_profile_does_not_change_execution_identity(tmp_path: Path) -> None:
    config_dir = _copy_real_config_tree(tmp_path)
    expected_config = resolve_project_configuration(
        config_dir=config_dir,
        bootstrap_settings=RuntimeBootstrapSettings(execution_profile="scientific"),
    )

    with open(config_dir / "runtime.yaml") as handle:
        runtime = yaml.safe_load(handle)
    # "development" is not the active profile in this test -- editing it must not move identity.
    runtime["execution_profiles"]["development"]["concurrency"]["worker_count"] = 999
    (config_dir / "runtime.yaml").write_text(yaml.safe_dump(runtime, sort_keys=False))

    current_config = resolve_project_configuration(
        config_dir=config_dir,
        bootstrap_settings=RuntimeBootstrapSettings(execution_profile="scientific"),
    )

    assert current_config.execution_fingerprint == expected_config.execution_fingerprint
    assert current_config.scientific_fingerprint == expected_config.scientific_fingerprint
