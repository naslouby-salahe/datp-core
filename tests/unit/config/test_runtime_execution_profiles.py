"""Resolved execution-profile record tests."""

from datp_core.config.runtime_settings import ExecutionProfileRecord, resolve_runtime_configuration
from datp_core.config.yaml_loader import YamlConfigurationReader
from pathlib import Path


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
