"""The scientific/execution fingerprint projections are built through one canonicalization
path (cattrs unstructure of pure domain records) -- never a second, Pydantic-specific
``model_dump`` path -- so there is exactly one authority for canonical serialization."""

from __future__ import annotations

import inspect

import attrs

from datp_core.config import resolver as resolver_module
from datp_core.config.resolver import _unstructure, resolve_project_configuration


def test_resolver_module_has_no_model_dump_call_in_the_fingerprint_projection_assembly() -> None:
    source = inspect.getsource(resolver_module)
    # The sole legitimate use is the Pydantic-to-domain-record conversion helper itself,
    # which runs before any fingerprint projection is assembled.
    call_sites = [line for line in source.splitlines() if ".model_dump(" in line]
    assert call_sites == ["    return record_type(**cfg.model_dump())"]


def test_threshold_policy_projection_uses_domain_field_names_not_pydantic_aliases() -> None:
    """A stray ``model_dump(mode="json")`` on the raw Pydantic model would have produced
    JSON-mode-specific formatting; the unified cattrs path must not reintroduce it."""
    config = resolve_project_configuration()
    policy_id = next(iter(config.threshold_policies))
    policy = config.threshold_policies.get(policy_id)

    # The domain record type itself must not be a Pydantic model (already covered by
    # test_threshold_policy_records.py) -- here we assert its unstructured projection form
    # is a plain dict keyed by the exact attrs field names, with no '$defs'/schema artifacts.
    projected = _unstructure(policy)
    assert isinstance(projected, dict)
    assert "$defs" not in projected
    assert set(projected) == {f.name for f in attrs.fields(type(policy))}
