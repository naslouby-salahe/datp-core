"""Strict PyYAML reader loading authored configuration files into Pydantic 2 models."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from .models.dataset_config import AuthoredDatasetConfig
from .models.experiment_config import AuthoredExperimentsCatalogueConfig
from .models.protocol_config import AuthoredProtocolsConfig
from .models.runtime_config import AuthoredRuntimeConfig

TModel = TypeVar("TModel", bound=BaseModel)


def load_authored_yaml[TModel: BaseModel](file_path: Path, model_cls: type[TModel]) -> TModel:
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file does not exist: {file_path}")
    raw_text = file_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration YAML at {file_path} must resolve to a dictionary")
    return model_cls.model_validate(data)


def load_dataset_config(file_path: Path) -> AuthoredDatasetConfig:
    return load_authored_yaml(file_path, AuthoredDatasetConfig)


def load_experiments_catalogue(file_path: Path) -> AuthoredExperimentsCatalogueConfig:
    return load_authored_yaml(file_path, AuthoredExperimentsCatalogueConfig)


def load_protocols_config(file_path: Path) -> AuthoredProtocolsConfig:
    return load_authored_yaml(file_path, AuthoredProtocolsConfig)


def load_runtime_config(file_path: Path) -> AuthoredRuntimeConfig:
    return load_authored_yaml(file_path, AuthoredRuntimeConfig)
