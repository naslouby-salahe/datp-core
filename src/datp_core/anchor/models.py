"""Tiny validator shared by comparison and reproduction detail fields."""


def _require_non_empty_detail(v: str) -> str:
    if not v:
        raise ValueError("detail must be non-empty")
    return v
