"""Shared fixtures for scientific-invariant tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from datp_core.config.loading import RuntimeBootstrapSettings
from datp_core.config.project import ResolvedProjectConfiguration, resolve_project_configuration


@pytest.fixture(scope="module")
def _resolved() -> ResolvedProjectConfiguration:
    os.environ.setdefault("DATP_EXECUTION_PROFILE", "scientific")
    return resolve_project_configuration(
        config_dir=Path("configs"),
        bootstrap_settings=RuntimeBootstrapSettings(),  # pyright: ignore[reportCallIssue]
    )
