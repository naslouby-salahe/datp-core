"""The scientific/execution fingerprint projections are built through one canonicalization
path (cattrs unstructure of pure domain records) -- never a second, Pydantic-specific
``model_dump`` path -- so there is exactly one authority for canonical serialization."""

from __future__ import annotations

import inspect

import attrs

from datp_core.config import protocol_resolution as protocol_module
from datp_core.config.converter import unstructure_projection
from datp_core.config.resolver import resolve_project_configuration


def test_protocol_resolution_module_has_no_model_dump_call_in_fingerprint_assembly() -> None:
    source = inspect.getsource(protocol_module)
    # The sole legitimate use is the Pydantic-to-domain-record conversion helper itself,
    # which runs before any fingerprint projection is assembled.
    call_sites = [line for line in source.splitlines() if ".model_dump(" in line]
    assert call_sites == ["    return record_type(**cfg.model_dump())"]


def test_threshold_policy_projection_uses_domain_field_names_not_pydantic_aliases() -> None:
    # cattrs unstructured projection must use attrs field names, never Pydantic JSON-mode aliases.
    config = resolve_project_configuration()
    policy_id = next(iter(config.threshold_policies))
    policy = config.threshold_policies.get(policy_id)

    # The domain record must not be Pydantic -- assert unstructured projection is a plain dict
    # keyed by exact attrs field names, with no '$defs'/schema artifacts.
    projected = unstructure_projection(policy)
    assert isinstance(projected, dict)
    assert "$defs" not in projected
    assert set(projected) == {f.name for f in attrs.fields(type(policy))}
