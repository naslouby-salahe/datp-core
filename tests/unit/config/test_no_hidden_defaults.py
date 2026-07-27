"""Conformance: resolved domain/runtime records carry no hidden defaults.

Every resolved record field must be supplied explicitly by the resolver (lossless resolution),
so scientific and selectable values can never originate from a dataclass default. The only
permitted defaults are empty-collection factories for genuinely optional collections, which are
listed on an explicit allowlist (mirroring the "framework-required defaults" conformance rule).
"""

from __future__ import annotations

import inspect

import attrs

import datp_core.config.loading as loading
import datp_core.config.resolution.runtime as runtime_resolution
import datp_core.data.contracts as datasets
import datp_core.experiments.catalogue.models as experiments
import datp_core.learning.contracts.architecture as learning_arch
import datp_core.learning.contracts.checkpoints as learning_chk
import datp_core.learning.contracts.enums as learning_enums
import datp_core.learning.contracts.optimization as learning_opt
import datp_core.learning.contracts.seeds as learning_seeds
import datp_core.learning.contracts.training as learning_train

# (class name, field name) pairs permitted to hold an empty-collection factory default.
_EMPTY_COLLECTION_ALLOWLIST = {
    ("ExperimentRecord", "sweeps"),
}

# Record fields that are genuinely optional (None when not authored in YAML).
_OPTIONAL_NONE_ALLOWLIST = {
    ("ConcurrencyRecord", "training_concurrency"),
    ("ConcurrencyRecord", "scoring_concurrency"),
    ("ConcurrencyRecord", "audit_concurrency"),
    ("ResourceBudgetRecord", "max_vram_gib"),
}

# Non-record attrs classes that are not part of the resolved configuration surface.
_EXCLUDED_CLASSES = {"RuntimeBootstrapSettings"}


def _is_empty_collection_factory(default: object) -> bool:
    if not isinstance(default, attrs.Factory):
        return False
    f = default.factory
    return f is tuple or f is list or f is dict or f is frozenset


def test_resolved_records_have_no_hidden_defaults() -> None:
    offenders: list[str] = []
    learning_modules = (learning_arch, learning_chk, learning_enums, learning_opt, learning_seeds, learning_train)
    for module in (experiments, *learning_modules, loading, runtime_resolution, datasets):
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
                if (class_name, field.name) in _OPTIONAL_NONE_ALLOWLIST and field.default is None:
                    continue
                offenders.append(f"{class_name}.{field.name} = {field.default!r}")
    assert offenders == [], f"Resolved records must not carry hidden defaults: {offenders}"
