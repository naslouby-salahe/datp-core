"""Canonical JSON serialization for publication records."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


def canonical_json_text(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json", round_trip=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_dataclass_json_text(value: object) -> str:
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError("canonical dataclass serialization requires a dataclass instance")
    return json.dumps(
        asdict(value),
        default=_json_default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def load_model_json(model_type: type[TModel], text: str) -> TModel:
    return model_type.model_validate_json(text)


def _json_default(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")
