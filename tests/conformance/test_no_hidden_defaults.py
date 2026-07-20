"""Conformance: resolved domain/runtime records carry no hidden defaults.

Every resolved record field must be supplied explicitly by the resolver (lossless resolution),
so scientific and selectable values can never originate from a dataclass default. The only
permitted defaults are empty-collection factories for genuinely optional collections, which are
listed on an explicit allowlist (mirroring the "framework-required defaults" conformance rule).
"""

from __future__ import annotations

import inspect

import attrs

import datp_core.config.runtime_settings as runtime_settings
import datp_core.domain.catalogue as catalogue

# (class name, field name) pairs permitted to hold an empty-collection factory default.
_EMPTY_COLLECTION_ALLOWLIST = {
    ("ExperimentRecord", "sweeps"),
}

# Non-record attrs classes that are not part of the resolved configuration surface.
_EXCLUDED_CLASSES = {"RuntimeBootstrapSettings"}


def _is_empty_collection_factory(default: object) -> bool:
    return isinstance(default, attrs.Factory) and default.factory in (tuple, list, dict, frozenset)  # type: ignore[arg-type]


def test_resolved_records_have_no_hidden_defaults() -> None:
    offenders: list[str] = []
    for module in (catalogue, runtime_settings):
        for class_name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__ or not attrs.has(cls) or class_name in _EXCLUDED_CLASSES:
                continue
            for field in attrs.fields(cls):
                if field.default is attrs.NOTHING:
                    continue
                if (class_name, field.name) in _EMPTY_COLLECTION_ALLOWLIST and _is_empty_collection_factory(
                    field.default
                ):
                    continue
                offenders.append(f"{class_name}.{field.name} = {field.default!r}")
    assert offenders == [], f"Resolved records must not carry hidden defaults: {offenders}"
