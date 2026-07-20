"""Minimal deterministic table renderer; scientific values are supplied as frozen inputs."""

from __future__ import annotations

from collections.abc import Sequence


def render_csv_table(headers: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> str:
    if any(len(row) != len(headers) for row in rows):
        raise ValueError("all report rows must match headers")

    def escaped(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    return "\n".join(",".join(escaped(value) for value in row) for row in (headers, *tuple(rows))) + "\n"
