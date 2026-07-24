"""Result freeze error."""

from __future__ import annotations


class ResultFreezeError(ValueError):
    """A result family cannot be safely frozen or rendered."""
