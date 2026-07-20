"""Structured logging configuration tests."""

import pytest

from datp_core.infrastructure.runtime.logging import configure_structured_logging


def test_logging_configuration_requires_declared_mode_and_level() -> None:
    with pytest.raises(ValueError, match="logging level"):
        configure_structured_logging("human", "TRACE")
    with pytest.raises(ValueError, match="logging mode"):
        configure_structured_logging("terminal", "INFO")
