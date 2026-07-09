"""Dataset identifiers (docs/protocol/artifact_contracts.md #1)."""

from __future__ import annotations

from enum import StrEnum


class DatasetId(StrEnum):
    N_BAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"
