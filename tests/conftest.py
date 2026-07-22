"""Shared test-session bootstrap configuration.

The active execution profile has no authored default in runtime.yaml and must be supplied
explicitly (env var or constructor argument) -- there is no code-level fallback. This fixture
sets that explicit test-environment convention once for the whole suite, exactly as a CI
pipeline or local `.env` would, rather than resurrecting a silent default in production code.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True, scope="session")
def _default_test_execution_profile() -> Iterator[None]:
    previous_profile = os.environ.get("DATP_EXECUTION_PROFILE")
    previous_root = os.environ.get("DATP_REPOSITORY_ROOT")
    os.environ.setdefault("DATP_EXECUTION_PROFILE", "scientific")
    os.environ.setdefault("DATP_REPOSITORY_ROOT", os.getcwd())
    try:
        yield
    finally:
        if previous_profile is None:
            os.environ.pop("DATP_EXECUTION_PROFILE", None)
        else:
            os.environ["DATP_EXECUTION_PROFILE"] = previous_profile
        if previous_root is None:
            os.environ.pop("DATP_REPOSITORY_ROOT", None)
        else:
            os.environ["DATP_REPOSITORY_ROOT"] = previous_root
