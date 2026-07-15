from dataclasses import dataclass, fields
from datetime import UTC, datetime
from hashlib import sha256
from inspect import signature
from pathlib import Path
from subprocess import run

import pytest

from datp_core.application.ports.runtime import (
    Clock,
    CodeStateProvider,
    DependencyLockStateProvider,
    EnvironmentInventoryProvider,
)
from datp_core.domain.artifacts.provenance import CodeState, DependencyLockState, EnvironmentInventory
from datp_core.domain.errors import EnvironmentIncompatibilityError
from datp_core.domain.learning.scores import ScoringBatchSpec
from datp_core.domain.learning.training import (
    ClientBatchPartitioning,
    DeterminismLevel,
    OptimizerStepSemantics,
    PrecisionMode,
    TrainingBatchSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, GradientAccumulationSteps, WorkerCount
from datp_core.domain.runtime.policies import DevicePolicy, DeviceSpec, HardwareInventory
from datp_core.infrastructure.runtime.provenance import (
    GitCodeStateProvider,
    RuntimeEnvironmentInventoryProvider,
    SystemClock,
    UvDependencyLockStateProvider,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FrozenClock:
    timestamp: datetime

    def now(self) -> datetime:
        return self.timestamp


@dataclass(frozen=True, slots=True, kw_only=True)
class StaticHardwareInspector:
    hardware: HardwareInventory

    def inspect(self) -> HardwareInventory:
        return self.hardware


def _lock_contents(*, include_msgspec: bool = True) -> bytes:
    packages = [
        ("scikit-learn", "1.9.0"),
        ("pyarrow", "25.0.0"),
        ("numpy", "2.5.1"),
        ("scipy", "1.18.0"),
        ("blake3", "1.0.9"),
    ]
    if include_msgspec:
        packages.append(("msgspec", "0.21.1"))
    return "\n".join(f'[[package]]\nname = "{name}"\nversion = "{version}"' for name, version in packages).encode()


def _initialize_repository(repository: Path) -> Path:
    _git(repository, "init")
    _git(repository, "config", "user.email", "provenance@example.invalid")
    _git(repository, "config", "user.name", "Provenance Test")
    tracked_file = repository / "tracked.txt"
    tracked_file.write_text("tracked\n")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-m", "initial")
    return tracked_file


def _git(repository: Path, *arguments: str) -> None:
    run(("git", "-C", str(repository), *arguments), check=True, capture_output=True)


def _training_batch() -> TrainingBatchSpec:
    return TrainingBatchSpec(
        micro_batch_size=BatchSize(value=1),
        gradient_accumulation_steps=GradientAccumulationSteps(value=1),
        effective_batch_size=BatchSize(value=1),
        dataloader_batch_size=BatchSize(value=1),
        client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
        optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
    )


def test_provenance_records_keep_the_exact_contract_fields() -> None:
    assert tuple(field.name for field in fields(CodeState)) == (
        "commit_identity",
        "is_dirty",
        "dirty_diff_hash",
        "source_package_version",
    )
    assert tuple(field.name for field in fields(DependencyLockState)) == (
        "lock_identity",
        "scikit_learn_version",
        "pyarrow_version",
        "numpy_version",
        "scipy_version",
        "blake3_version",
        "msgspec_version",
    )
    assert tuple(field.name for field in fields(EnvironmentInventory)) == (
        "hardware",
        "selected_device",
        "precision",
        "determinism",
        "training_batch",
        "scoring_batch",
        "dataloader_workers",
        "scikit_learn_version",
        "pyarrow_version",
        "numpy_version",
        "scipy_version",
        "blake3_version",
        "msgspec_version",
    )


def test_provenance_providers_match_their_ports() -> None:
    assert signature(GitCodeStateProvider.inspect) == signature(CodeStateProvider.inspect)
    assert signature(UvDependencyLockStateProvider.inspect) == signature(DependencyLockStateProvider.inspect)
    assert signature(RuntimeEnvironmentInventoryProvider.inspect) == signature(EnvironmentInventoryProvider.inspect)
    assert signature(SystemClock.now) == signature(Clock.now)


def test_synthetic_clean_and_tracked_dirty_checkouts_are_distinguished(tmp_path: Path) -> None:
    tracked_file = _initialize_repository(tmp_path)
    provider = GitCodeStateProvider(repository=tmp_path, package_distribution="not-installed")

    clean = provider.inspect()
    tracked_file.write_text("tracked\n \n")
    dirty = provider.inspect()
    tracked_file.write_text("tracked\n  \n")
    changed_whitespace = provider.inspect()

    assert clean.is_dirty is False
    assert clean.dirty_diff_hash is None
    assert dirty.is_dirty is True
    assert dirty.dirty_diff_hash is not None
    assert dirty.dirty_diff_hash != changed_whitespace.dirty_diff_hash
    assert clean.commit_identity == dirty.commit_identity


def test_unavailable_vcs_state_is_explicitly_absent_not_reported_clean(tmp_path: Path) -> None:
    state = GitCodeStateProvider(repository=tmp_path, package_distribution="not-installed").inspect()

    assert state.commit_identity is None
    assert state.is_dirty is None
    assert state.dirty_diff_hash is None


def test_dependency_lock_state_matches_the_synthetic_committed_lock_exactly(tmp_path: Path) -> None:
    lock_contents = _lock_contents()
    lock_path = tmp_path / "uv.lock"
    lock_path.write_bytes(lock_contents)

    state = UvDependencyLockStateProvider(lock_path=lock_path).inspect()

    assert state == DependencyLockState(
        lock_identity=sha256(lock_contents).hexdigest(),
        scikit_learn_version="1.9.0",
        pyarrow_version="25.0.0",
        numpy_version="2.5.1",
        scipy_version="1.18.0",
        blake3_version="1.0.9",
        msgspec_version="0.21.1",
    )


def test_missing_required_lock_version_raises_a_typed_environment_error(tmp_path: Path) -> None:
    lock_path = tmp_path / "uv.lock"
    lock_path.write_bytes(_lock_contents(include_msgspec=False))

    with pytest.raises(EnvironmentIncompatibilityError, match="required dependency lock value is unavailable"):
        UvDependencyLockStateProvider(lock_path=lock_path).inspect()


def test_environment_inventory_uses_lock_versions_and_an_explicit_frozen_clock() -> None:
    timestamp = datetime(2026, 7, 15, tzinfo=UTC)
    clock = FrozenClock(timestamp=timestamp)
    lock_state = DependencyLockState(
        lock_identity="a" * 64,
        scikit_learn_version="1.9.0",
        pyarrow_version="25.0.0",
        numpy_version="2.5.1",
        scipy_version="1.18.0",
        blake3_version="1.0.9",
        msgspec_version="0.21.1",
    )
    inventory = RuntimeEnvironmentInventoryProvider(
        hardware_inspector=StaticHardwareInspector(
            hardware=HardwareInventory(
                cuda_available=False,
                gpu_name=None,
                gpu_count=0,
                vram_bytes=None,
                torch_version="2.10.0",
                cuda_runtime=None,
                driver_version=None,
                cpu_count=1,
                ram_bytes=None,
            )
        ),
        dependency_lock_state_provider=_StaticLockStateProvider(lock_state=lock_state),
        selected_device=DeviceSpec(policy=DevicePolicy.CPU_ALLOWED, gpu_index=None),
        precision=PrecisionMode.FP32,
        determinism=DeterminismLevel.STRICT,
        training_batch=_training_batch(),
        scoring_batch=ScoringBatchSpec(
            calibration_batch_size=BatchSize(value=1),
            test_batch_size=BatchSize(value=1),
            temporal_batch_size=BatchSize(value=1),
        ),
        dataloader_workers=WorkerCount(value=0),
    ).inspect()

    assert clock.now() == timestamp
    assert inventory.scikit_learn_version == lock_state.scikit_learn_version
    assert inventory.msgspec_version == lock_state.msgspec_version


@dataclass(frozen=True, slots=True, kw_only=True)
class _StaticLockStateProvider:
    lock_state: DependencyLockState

    def inspect(self) -> DependencyLockState:
        return self.lock_state
