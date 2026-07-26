"""Unit tests for AnalysisRunner single-dispatch dispatching."""

from __future__ import annotations

import pytest
from attrs import define

from datp_core.analysis.errors import UnsupportedAnalysisRecordError
from datp_core.analysis.runtime.runner import register_analysis_capabilities, run_analysis


@define(frozen=True, slots=True)
class UnsupportedRecordSpec:
    label: str = "unsupported"


def test_runner_capabilities_registration() -> None:
    register_analysis_capabilities()
    # Attempting to re-register capabilities is idempotent
    register_analysis_capabilities()


def test_runner_rejects_unregistered_specification(monkeypatch: pytest.MonkeyPatch) -> None:
    register_analysis_capabilities()
    spec = UnsupportedRecordSpec()
    with pytest.raises(UnsupportedAnalysisRecordError):
        run_analysis(spec, context=None)  # type: ignore[arg-type]
