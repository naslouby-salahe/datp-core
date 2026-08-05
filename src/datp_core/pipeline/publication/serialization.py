"""Canonical JSON document persistence for experiment publications."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel

from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values import Checksum, checksum_text


def canonical_model_json_text(model: BaseModel) -> str:
    return canonical_json_text(model)


def serialize_json_model(model: BaseModel, destination: Path) -> Checksum:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_text(model)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file.write(payload)
        temporary_path = Path(temporary_file.name)
    try:
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return checksum_text(payload)


def load_model_json[ModelT: BaseModel](model_type: type[ModelT], text: str) -> ModelT:
    return model_type.model_validate_json(text)


def load_model_file[ModelT: BaseModel](model_type: type[ModelT], path: Path) -> ModelT:
    return load_model_json(model_type, path.read_text(encoding="utf-8"))
