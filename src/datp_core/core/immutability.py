"""Deep freezing and immutable projection helpers — all callers now use direct dict() conversion.

This module previously exported deep_freeze, FrozenJson, freeze_json, and the as_*_mapping
family. Every caller has been migrated to plain dict()/tuple() with Pydantic BeforeValidator.
Retained as an empty module to avoid breaking any dynamic import.
"""
