"""Application use cases for configuration validation, catalogue description, and drift explanation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deepdiff import DeepDiff

from datp_core.config.resolver import resolve_catalogue
from datp_core.config.validation import validate_all_configurations
from datp_core.config.yaml_loader import load_authored_yaml
from datp_core.domain.catalogue import ResolvedCatalogue


class ValidateConfigurationUseCase:
    def execute(self, config_slug: str | None = None) -> bool:
        validate_all_configurations()
        return True


class DescribeCatalogueUseCase:
    def execute(self) -> ResolvedCatalogue:
        return resolve_catalogue()


class ExplainConfigurationDriftUseCase:
    def execute(self, current_yaml_path: Path, expected_yaml_path: Path) -> dict[str, Any]:
        curr = load_authored_yaml(current_yaml_path, type(None)) # type: ignore
        exp = load_authored_yaml(expected_yaml_path, type(None)) # type: ignore
        diff = DeepDiff(exp, curr, ignore_order=True)
        return dict(diff)
