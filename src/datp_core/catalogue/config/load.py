"""Duplicate-safe loading of exactly the six authoritative YAML documents."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from pydantic import BaseModel, ValidationError
from yaml import SafeLoader, YAMLError, load
from yaml.nodes import MappingNode

from ...kernel.errors import ConfigurationError
from .bundle import (
    AuthoredConfigBundle,
    AuthoredMapping,
    AuthoredValue,
    ConfigPaths,
    DatasetDocumentConfig,
    ExperimentsDocumentConfig,
    ProtocolsDocumentConfig,
    RuntimeDocumentConfig,
)


class _DuplicateKeyLoader(SafeLoader):
    pass


class _PairConstructingLoader(Protocol):
    def construct_pairs(self, node: MappingNode, deep: bool = False) -> list[tuple[object, object]]: ...


def _authored_value(value: object) -> AuthoredValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        items = cast("list[object]", value)
        return [_authored_value(item) for item in items]
    if isinstance(value, dict):
        mapping: AuthoredMapping = {}
        items = cast("dict[object, object]", value)
        for key, item in items.items():
            canonical_key = str(key)
            if canonical_key in mapping:
                raise ConfigurationError(f"duplicate YAML key after canonicalization: {canonical_key}")
            mapping[canonical_key] = _authored_value(item)
        return mapping
    raise ConfigurationError(f"unsupported YAML value type: {type(value).__name__}")


def _mapping(loader: _DuplicateKeyLoader, node: MappingNode, deep: bool = False) -> AuthoredMapping:
    pairs = cast(_PairConstructingLoader, loader).construct_pairs(node, deep=True)
    result: AuthoredMapping = {}
    for raw_key, raw_value in pairs:
        key = str(raw_key)
        if key in result:
            raise ConfigurationError(f"duplicate YAML key: {key!s}")
        result[key] = _authored_value(raw_value)
    return result


_DuplicateKeyLoader.add_constructor("tag:yaml.org,2002:map", _mapping)


def _read[TDocument: BaseModel](path: Path, model: type[TDocument]) -> TDocument:
    try:
        parsed: object = load(path.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader)
    except (OSError, YAMLError, ConfigurationError) as error:
        raise ConfigurationError(f"{path}: {error}") from error
    if not isinstance(parsed, dict):
        raise ConfigurationError(f"{path}: root must be a mapping")
    try:
        return model.model_validate(_authored_value(cast(object, parsed)))
    except ValidationError as error:
        raise ConfigurationError(f"{path}: {error}") from error


def load_authored_bundle(paths: ConfigPaths) -> AuthoredConfigBundle:
    datasets = (
        _read(paths.nbaiot, DatasetDocumentConfig),
        _read(paths.ciciot2023, DatasetDocumentConfig),
        _read(paths.edge_iiotset, DatasetDocumentConfig),
    )
    identifiers = tuple(document.dataset for document in datasets)
    if len(set(identifiers)) != len(identifiers):
        raise ConfigurationError("dataset identifiers must be unique")
    return AuthoredConfigBundle(
        datasets=datasets,
        experiments=_read(paths.experiments, ExperimentsDocumentConfig),
        protocols=_read(paths.protocols, ProtocolsDocumentConfig),
        runtime=_read(paths.runtime, RuntimeDocumentConfig),
    )
