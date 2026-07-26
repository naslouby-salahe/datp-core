"""Unit tests for AnalysisResultRegistry."""

from __future__ import annotations

from typing import ClassVar

import pytest
from attrs import define

from datp_core.analysis.enums import AnalysisResultKind
from datp_core.analysis.errors import (
    DuplicateResultKindError,
    DuplicateResultTypeError,
    ResultRegistryError,
    UnknownResultKindError,
    UnsupportedPayloadVersionError,
)
from datp_core.analysis.runtime.registry import RESULT_REGISTRY, AnalysisResultRegistry, ResultKindEntry


@define(frozen=True, slots=True, kw_only=True)
class DummyResultA:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.PAIRED_THRESHOLD
    payload_version: ClassVar[int] = 1


@define(frozen=True, slots=True, kw_only=True)
class DummyResultB:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION
    payload_version: ClassVar[int] = 1


def test_registry_register_and_lookup() -> None:
    reg = AnalysisResultRegistry()
    entry = ResultKindEntry(
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
        result_type=DummyResultA,  # type: ignore[arg-type]
        payload_version=1,
    )
    reg.register(entry)

    assert reg.get(AnalysisResultKind.PAIRED_THRESHOLD) == entry
    dummy = DummyResultA()
    assert reg.kind_for(dummy) == AnalysisResultKind.PAIRED_THRESHOLD
    assert reg.type_for(AnalysisResultKind.PAIRED_THRESHOLD) == DummyResultA


def test_registry_rejects_duplicate_kind() -> None:
    reg = AnalysisResultRegistry()
    entry1 = ResultKindEntry(
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
        result_type=DummyResultA,  # type: ignore[arg-type]
        payload_version=1,
    )
    entry2 = ResultKindEntry(
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
        result_type=DummyResultB,  # type: ignore[arg-type]
        payload_version=1,
    )
    reg.register(entry1)
    with pytest.raises(DuplicateResultKindError):
        reg.register(entry2)


def test_registry_rejects_duplicate_type() -> None:
    reg = AnalysisResultRegistry()
    entry1 = ResultKindEntry(
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
        result_type=DummyResultA,  # type: ignore[arg-type]
        payload_version=1,
    )
    entry2 = ResultKindEntry(
        result_kind=AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION,
        result_type=DummyResultA,  # type: ignore[arg-type]
        payload_version=1,
    )
    reg.register(entry1)
    with pytest.raises(DuplicateResultTypeError):
        reg.register(entry2)


def test_registry_rejects_invalid_payload_version() -> None:
    reg = AnalysisResultRegistry()
    entry = ResultKindEntry(
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
        result_type=DummyResultA,  # type: ignore[arg-type]
        payload_version=0,
    )
    with pytest.raises(UnsupportedPayloadVersionError):
        reg.register(entry)


def test_registry_rejects_unknown_kind() -> None:
    reg = AnalysisResultRegistry()
    with pytest.raises(UnknownResultKindError):
        reg.get(AnalysisResultKind.PAIRED_THRESHOLD)


def test_registry_rejects_unregistered_instance() -> None:
    reg = AnalysisResultRegistry()
    with pytest.raises(ResultRegistryError):
        reg.kind_for(DummyResultA())


def test_global_result_registry_has_registrations() -> None:
    from datp_core.analysis.runtime.runner import register_analysis_capabilities

    register_analysis_capabilities()
    assert RESULT_REGISTRY.get(AnalysisResultKind.PAIRED_THRESHOLD) is not None
