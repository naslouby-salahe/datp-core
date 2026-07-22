"""Strict PyYAML reader loading authored configuration files into Pydantic 2 models."""

from __future__ import annotations

from collections.abc import Hashable
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from pydantic import BaseModel, JsonValue, ValidationError

from datp_core.config.models.dataset_config import AuthoredDatasetConfig
from datp_core.config.models.experiment_config import AuthoredExperimentsCatalogueConfig
from datp_core.config.models.protocol_config import AuthoredProtocolsConfig
from datp_core.config.models.runtime_config import AuthoredRuntimeConfig

TModel = TypeVar("TModel", bound=BaseModel)


class ConfigurationError(Exception):
    """Typed error for configuration loading, duplicate key, or schema validation failures."""

    def __init__(self, message: str, source_path: Path | None = None, cause: Exception | None = None) -> None:
        formatted = f"[{source_path}] {message}" if source_path else message
        super().__init__(formatted)
        self.source_path = source_path
        self.cause = cause


class _DuplicateCheckingSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Hashable, Any]:
        mapping: dict[Hashable, Any] = {}
        for key_node, value_node in node.value:
            key = cast(Hashable, self.construct_object(key_node, deep=deep))
            if key in mapping:
                line = key_node.start_mark.line + 1
                col = key_node.start_mark.column + 1
                raise ConfigurationError(f"Duplicate YAML key '{key}' found at line {line}, column {col}")
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


class YamlConfigurationReader:
    """Cohesive strict configuration reader loading YAML documents into validated Pydantic models."""

    @staticmethod
    def read_document(file_path: Path) -> dict[str, JsonValue]:
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file does not exist: {file_path}", source_path=file_path)
        try:
            raw_text = file_path.read_text(encoding="utf-8")
            data = yaml.load(raw_text, Loader=_DuplicateCheckingSafeLoader)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"YAML parsing error: {exc}", source_path=file_path, cause=exc) from exc
        except ConfigurationError as exc:
            exc.source_path = file_path
            raise exc

        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Configuration YAML root must resolve to a mapping, got {type(data).__name__}",
                source_path=file_path,
            )
        return cast(dict[str, JsonValue], data)

    @classmethod
    def read_model(cls, file_path: Path, model_cls: type[TModel]) -> TModel:
        if model_cls is type(None) or not issubclass(model_cls, BaseModel):
            raise ConfigurationError(f"Invalid model class: {model_cls}", source_path=file_path)
        data = cls.read_document(file_path)
        try:
            return model_cls.model_validate(data)
        except ValidationError as exc:
            raise ConfigurationError(
                f"Schema validation failed for {model_cls.__name__}:\n{exc}",
                source_path=file_path,
                cause=exc,
            ) from exc

    @classmethod
    def read_dataset_document(cls, file_path: Path) -> AuthoredDatasetConfig:
        return cls.read_model(file_path, AuthoredDatasetConfig)

    @classmethod
    def read_experiments_document(cls, file_path: Path) -> AuthoredExperimentsCatalogueConfig:
        return cls.read_model(file_path, AuthoredExperimentsCatalogueConfig)

    @classmethod
    def read_protocols_document(cls, file_path: Path) -> AuthoredProtocolsConfig:
        return cls.read_model(file_path, AuthoredProtocolsConfig)

    @classmethod
    def read_runtime_document(cls, file_path: Path) -> AuthoredRuntimeConfig:
        return cls.read_model(file_path, AuthoredRuntimeConfig)

    @classmethod
    def read_project_documents(
        cls,
        dataset_paths: tuple[Path, ...],
        experiments_path: Path,
        protocols_path: Path,
        runtime_path: Path,
    ) -> tuple[
        tuple[AuthoredDatasetConfig, ...],
        AuthoredExperimentsCatalogueConfig,
        AuthoredProtocolsConfig,
        AuthoredRuntimeConfig,
    ]:
        datasets = tuple(cls.read_dataset_document(p) for p in dataset_paths)
        experiments = cls.read_experiments_document(experiments_path)
        protocols = cls.read_protocols_document(protocols_path)
        runtime = cls.read_runtime_document(runtime_path)
        return datasets, experiments, protocols, runtime
