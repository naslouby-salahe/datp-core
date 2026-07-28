"""Typed data-package failures."""

from __future__ import annotations

from pathlib import Path

from datp_core.data.contracts.enums import DataFailureCode


class DataFailure(RuntimeError):  # noqa: N818
    def __init__(
        self,
        code: DataFailureCode,
        detail: str,
        *,
        source_path: Path | None,
        source_row_index: int | None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.source_path = source_path
        self.source_row_index = source_row_index
        location = ""
        if source_path is not None:
            location = f" [{source_path.as_posix()}"
            if source_row_index is not None:
                location += f":{source_row_index}"
            location += "]"
        super().__init__(f"{code.value}: {detail}{location}")
