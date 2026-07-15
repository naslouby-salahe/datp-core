from dataclasses import dataclass
from enum import StrEnum

from datp_core.application.ports.telemetry import LogFormat, LogSink
from datp_core.domain.artifacts.keys import ArtifactRetentionPolicy
from datp_core.domain.errors import TestProfileValidationError
from datp_core.domain.runtime.admissibility import RamBudgetBytes, VramFraction


class TestSuiteKind(StrEnum):
    UNIT = "unit"
    PROPERTY = "property"
    CONTRACT = "contract"
    ARCHITECTURE = "architecture"
    INTEGRATION = "integration"
    CUDA = "cuda"
    GOLDEN = "golden"
    SYSTEM_SYNTHETIC = "system_synthetic"
    SCIENTIFIC_SMOKE = "scientific_smoke"


class TestDataScale(StrEnum):
    SYNTHETIC_TINY = "synthetic_tiny"
    SYNTHETIC_SMALL = "synthetic_small"
    REAL_SUBSAMPLE = "real_subsample"
    REAL_FULL = "real_full"


class TestIsolationMode(StrEnum):
    IN_MEMORY = "in_memory"
    TMP_SANDBOX = "tmp_sandbox"
    SHARED_READONLY_FIXTURE = "shared_readonly_fixture"


class TestDeviceRequirement(StrEnum):
    CPU_ONLY = "cpu_only"
    CUDA_REQUIRED = "cuda_required"
    CUDA_OPTIONAL = "cuda_optional"


class TestParallelismMode(StrEnum):
    XDIST_SAFE = "xdist_safe"
    SERIAL_ONLY = "serial_only"
    SERIAL_CUDA_LANE = "serial_cuda_lane"


class ExternalDependencyPolicy(StrEnum):
    NO_NETWORK = "no_network"
    NO_REAL_DATA = "no_real_data"
    REAL_DATA_ALLOWED = "real_data_allowed"


class TestOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    XFAILED = "xfailed"
    ERROR = "error"


@dataclass(frozen=True, slots=True, kw_only=True)
class TestResourceBudget:
    max_ram: RamBudgetBytes
    max_vram_fraction: VramFraction | None
    timeout_seconds: int

    def __post_init__(self) -> None:
        if (
            type(self.max_ram) is not RamBudgetBytes
            or (self.max_vram_fraction is not None and type(self.max_vram_fraction) is not VramFraction)
            or type(self.timeout_seconds) is not int
            or self.timeout_seconds < 1
        ):
            raise TestProfileValidationError(
                detail="test resource budget requires typed limits and a positive timeout",
                profile="unresolved",
                violation="typed limits and timeout_seconds >= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TestArtifactPolicy:
    isolation: TestIsolationMode
    retention: ArtifactRetentionPolicy

    def __post_init__(self) -> None:
        if type(self.isolation) is not TestIsolationMode or type(self.retention) is not ArtifactRetentionPolicy:
            raise TestProfileValidationError(
                detail="test artifact policy requires typed isolation and retention",
                profile="unresolved",
                violation="TestIsolationMode and ArtifactRetentionPolicy",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TestLoggingSpec:
    sink: LogSink
    fmt: LogFormat

    def __post_init__(self) -> None:
        if type(self.sink) is not LogSink or type(self.fmt) is not LogFormat:
            raise TestProfileValidationError(
                detail="test logging requires the canonical telemetry sink and format",
                profile="unresolved",
                violation="LogSink and LogFormat",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TestProfileSpec:
    suite: TestSuiteKind
    data_scale: TestDataScale
    isolation: TestIsolationMode
    device_requirement: TestDeviceRequirement
    parallelism: TestParallelismMode
    external_dependencies: ExternalDependencyPolicy
    resource_budget: TestResourceBudget
    artifact_policy: TestArtifactPolicy
    logging: TestLoggingSpec

    def __post_init__(self) -> None:
        if not _has_typed_test_profile_components(self):
            raise TestProfileValidationError(
                detail="test profile requires every typed execution component",
                profile="unresolved",
                violation="complete typed test profile",
            )
        if self.isolation is not self.artifact_policy.isolation:
            raise TestProfileValidationError(
                detail="test profile isolation must match its artifact policy",
                profile="unresolved",
                violation="matching TestIsolationMode",
            )


def _has_typed_test_profile_components(profile: TestProfileSpec) -> bool:
    return all(
        (
            type(profile.suite) is TestSuiteKind,
            type(profile.data_scale) is TestDataScale,
            type(profile.isolation) is TestIsolationMode,
            type(profile.device_requirement) is TestDeviceRequirement,
            type(profile.parallelism) is TestParallelismMode,
            type(profile.external_dependencies) is ExternalDependencyPolicy,
            type(profile.resource_budget) is TestResourceBudget,
            type(profile.artifact_policy) is TestArtifactPolicy,
            type(profile.logging) is TestLoggingSpec,
        )
    )
