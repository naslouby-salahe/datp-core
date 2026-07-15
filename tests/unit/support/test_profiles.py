from dataclasses import fields
from pathlib import Path

import pytest
from tests.support import profiles

from datp_core.application.ports.telemetry import LogFormat, LogSink
from datp_core.domain.artifacts.keys import ArtifactRetentionPolicy
from datp_core.domain.errors import TestProfileValidationError as ProfileValidationError
from datp_core.domain.runtime.admissibility import RamBudgetBytes, VramFraction


def _profile() -> profiles.TestProfileSpec:
    isolation = profiles.TestIsolationMode.TMP_SANDBOX
    return profiles.TestProfileSpec(
        suite=profiles.TestSuiteKind.UNIT,
        data_scale=profiles.TestDataScale.SYNTHETIC_TINY,
        isolation=isolation,
        device_requirement=profiles.TestDeviceRequirement.CPU_ONLY,
        parallelism=profiles.TestParallelismMode.XDIST_SAFE,
        external_dependencies=profiles.ExternalDependencyPolicy.NO_REAL_DATA,
        resource_budget=profiles.TestResourceBudget(
            max_ram=RamBudgetBytes(value=1024),
            max_vram_fraction=VramFraction(value=0.5),
            timeout_seconds=60,
        ),
        artifact_policy=profiles.TestArtifactPolicy(
            isolation=isolation,
            retention=ArtifactRetentionPolicy.DISCARD_ON_SUCCESS,
        ),
        logging=profiles.TestLoggingSpec(sink=LogSink.CONSOLE, fmt=LogFormat.HUMAN_READABLE),
    )


def test_test_support_vocabulary_is_closed_and_uses_canonical_retention() -> None:
    assert tuple(profiles.TestSuiteKind) == (
        profiles.TestSuiteKind.UNIT,
        profiles.TestSuiteKind.PROPERTY,
        profiles.TestSuiteKind.CONTRACT,
        profiles.TestSuiteKind.ARCHITECTURE,
        profiles.TestSuiteKind.INTEGRATION,
        profiles.TestSuiteKind.CUDA,
        profiles.TestSuiteKind.GOLDEN,
        profiles.TestSuiteKind.SYSTEM_SYNTHETIC,
        profiles.TestSuiteKind.SCIENTIFIC_SMOKE,
    )
    assert tuple(profiles.TestDataScale) == (
        profiles.TestDataScale.SYNTHETIC_TINY,
        profiles.TestDataScale.SYNTHETIC_SMALL,
        profiles.TestDataScale.REAL_SUBSAMPLE,
        profiles.TestDataScale.REAL_FULL,
    )
    assert tuple(profiles.TestIsolationMode) == (
        profiles.TestIsolationMode.IN_MEMORY,
        profiles.TestIsolationMode.TMP_SANDBOX,
        profiles.TestIsolationMode.SHARED_READONLY_FIXTURE,
    )
    assert tuple(profiles.TestDeviceRequirement) == (
        profiles.TestDeviceRequirement.CPU_ONLY,
        profiles.TestDeviceRequirement.CUDA_REQUIRED,
        profiles.TestDeviceRequirement.CUDA_OPTIONAL,
    )
    assert tuple(profiles.TestParallelismMode) == (
        profiles.TestParallelismMode.XDIST_SAFE,
        profiles.TestParallelismMode.SERIAL_ONLY,
        profiles.TestParallelismMode.SERIAL_CUDA_LANE,
    )
    assert tuple(profiles.ExternalDependencyPolicy) == (
        profiles.ExternalDependencyPolicy.NO_NETWORK,
        profiles.ExternalDependencyPolicy.NO_REAL_DATA,
        profiles.ExternalDependencyPolicy.REAL_DATA_ALLOWED,
    )
    assert profiles.ArtifactRetentionPolicy is ArtifactRetentionPolicy
    assert tuple(profiles.TestOutcome) == (
        profiles.TestOutcome.PASSED,
        profiles.TestOutcome.FAILED,
        profiles.TestOutcome.SKIPPED,
        profiles.TestOutcome.XFAILED,
        profiles.TestOutcome.ERROR,
    )


def test_profile_composes_only_typed_components() -> None:
    profile = _profile()

    assert tuple(field.name for field in fields(profile)) == (
        "suite",
        "data_scale",
        "isolation",
        "device_requirement",
        "parallelism",
        "external_dependencies",
        "resource_budget",
        "artifact_policy",
        "logging",
    )
    assert profile.artifact_policy.isolation is profile.isolation


def test_profile_rejects_conflicting_isolation() -> None:
    profile = _profile()

    with pytest.raises(ProfileValidationError, match="isolation"):
        profiles.TestProfileSpec(
            suite=profile.suite,
            data_scale=profile.data_scale,
            isolation=profiles.TestIsolationMode.IN_MEMORY,
            device_requirement=profile.device_requirement,
            parallelism=profile.parallelism,
            external_dependencies=profile.external_dependencies,
            resource_budget=profile.resource_budget,
            artifact_policy=profile.artifact_policy,
            logging=profile.logging,
        )


def test_pyproject_has_markers_but_no_test_profile_data() -> None:
    pyproject = (Path(__file__).parents[3] / "pyproject.toml").read_text()

    assert "markers =" in pyproject
    assert "[tool.datp.test-profile" not in pyproject
