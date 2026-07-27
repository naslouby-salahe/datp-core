"""Unit tests for AnalysisHandlerRegistry dispatching."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datp_core.analysis.errors import DuplicateAnalysisRegistrationError, UnsupportedAnalysisRecordError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import AnalysisHandlerRegistry
from datp_core.experiments.catalogue.analyses import AnalysisKind


def test_registry_rejects_duplicate_kind() -> None:
    registry = AnalysisHandlerRegistry()
    registry.register(AnalysisKind.THRESHOLD_STABILITY, lambda *args: ())

    with pytest.raises(DuplicateAnalysisRegistrationError):
        registry.register(AnalysisKind.THRESHOLD_STABILITY, lambda *args: ())


def test_registry_rejects_unregistered_kind() -> None:
    registry = AnalysisHandlerRegistry()
    spec = MagicMock()  # Union type - no single spec available
    spec.kind = AnalysisKind.PAIRED_THRESHOLD.value

    with pytest.raises(UnsupportedAnalysisRecordError):
        registry.dispatch(spec, context=MagicMock(spec=AnalysisExecutionContext))  # type: ignore[arg-type]
