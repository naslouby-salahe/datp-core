from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from subprocess import CalledProcessError, run

from datp_core.application.ports.runtime import (
    DependencyLockStateProvider,
    HardwareInspector,
)
from datp_core.domain.artifacts.provenance import CodeState, DependencyLockState, EnvironmentInventory
from datp_core.domain.errors import EnvironmentIncompatibilityError
from datp_core.domain.learning.scores import ScoringBatchSpec
from datp_core.domain.learning.training import DeterminismLevel, PrecisionMode, TrainingBatchSpec
from datp_core.domain.runtime.admissibility import WorkerCount
from datp_core.domain.runtime.policies import DeviceSpec

_REQUIRED_LOCK_PACKAGES = (
    "scikit-learn",
    "pyarrow",
    "numpy",
    "scipy",
    "blake3",
    "msgspec",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class GitCodeStateProvider:
    repository: Path
    package_distribution: str

    def inspect(self) -> CodeState:
        status = _git_output(self.repository, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        if status is None:
            return CodeState(
                commit_identity=None,
                is_dirty=None,
                dirty_diff_hash=None,
                source_package_version=_package_version(self.package_distribution),
            )
        is_dirty = bool(status)
        return CodeState(
            commit_identity=_git_text(self.repository, "rev-parse", "HEAD"),
            is_dirty=is_dirty,
            dirty_diff_hash=_dirty_diff_hash(self.repository) if is_dirty else None,
            source_package_version=_package_version(self.package_distribution),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class UvDependencyLockStateProvider:
    lock_path: Path

    def inspect(self) -> DependencyLockState:
        try:
            lock_contents = self.lock_path.read_bytes()
        except OSError as error:
            raise _missing_lock_value(self.lock_path.name) from error
        locked_versions = _locked_versions(lock_contents)
        _require_locked_packages(locked_versions)
        return DependencyLockState(
            lock_identity=sha256(lock_contents).hexdigest(),
            scikit_learn_version=locked_versions["scikit-learn"],
            pyarrow_version=locked_versions["pyarrow"],
            numpy_version=locked_versions["numpy"],
            scipy_version=locked_versions["scipy"],
            blake3_version=locked_versions["blake3"],
            msgspec_version=locked_versions["msgspec"],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeEnvironmentInventoryProvider:
    hardware_inspector: HardwareInspector
    dependency_lock_state_provider: DependencyLockStateProvider
    selected_device: DeviceSpec
    precision: PrecisionMode
    determinism: DeterminismLevel
    training_batch: TrainingBatchSpec
    scoring_batch: ScoringBatchSpec
    dataloader_workers: WorkerCount

    def inspect(self) -> EnvironmentInventory:
        lock_state = self.dependency_lock_state_provider.inspect()
        return EnvironmentInventory(
            hardware=self.hardware_inspector.inspect(),
            selected_device=self.selected_device,
            precision=self.precision,
            determinism=self.determinism,
            training_batch=self.training_batch,
            scoring_batch=self.scoring_batch,
            dataloader_workers=self.dataloader_workers,
            scikit_learn_version=lock_state.scikit_learn_version,
            pyarrow_version=lock_state.pyarrow_version,
            numpy_version=lock_state.numpy_version,
            scipy_version=lock_state.scipy_version,
            blake3_version=lock_state.blake3_version,
            msgspec_version=lock_state.msgspec_version,
        )


def _git_output(repository: Path, *arguments: str) -> bytes | None:
    try:
        return run(
            ("git", "-C", str(repository), *arguments),
            check=True,
            capture_output=True,
        ).stdout
    except (CalledProcessError, FileNotFoundError):
        return None


def _git_text(repository: Path, *arguments: str) -> str | None:
    output = _git_output(repository, *arguments)
    return output.decode().strip() if output is not None else None


def _dirty_diff_hash(repository: Path) -> str | None:
    diff = _git_output(repository, "diff", "--binary", "--no-ext-diff", "HEAD")
    untracked = _git_output(repository, "ls-files", "--others", "--exclude-standard", "-z")
    if diff is None or untracked is None:
        return None
    try:
        untracked_contents = _untracked_contents(repository, untracked)
    except OSError:
        return None
    return sha256(b"diff\0" + diff + b"untracked\0" + untracked_contents).hexdigest()


def _untracked_contents(repository: Path, paths: bytes) -> bytes:
    contents = bytearray()
    for relative_path in paths.split(b"\0"):
        if not relative_path:
            continue
        decoded_path = relative_path.decode()
        contents.extend(relative_path)
        contents.extend(b"\0")
        contents.extend((repository / decoded_path).read_bytes())
        contents.extend(b"\0")
    return bytes(contents)


def _package_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _locked_versions(lock_contents: bytes) -> dict[str, str]:
    versions: dict[str, str] = {}
    package_name: str | None = None
    for line in lock_contents.decode().splitlines():
        if line == "[[package]]":
            package_name = None
        elif line.startswith("name = "):
            package_name = _quoted_value(line)
        elif package_name is not None and line.startswith("version = "):
            versions[package_name] = _quoted_value(line)
    return versions


def _quoted_value(line: str) -> str:
    _, _, value = line.partition("=")
    return value.strip().strip('"')


def _require_locked_packages(locked_versions: dict[str, str]) -> None:
    for package_name in _REQUIRED_LOCK_PACKAGES:
        if package_name not in locked_versions:
            raise _missing_lock_value(package_name)


def _missing_lock_value(required: str) -> EnvironmentIncompatibilityError:
    return EnvironmentIncompatibilityError(
        detail="required dependency lock value is unavailable",
        required=required,
        present="absent",
    )
