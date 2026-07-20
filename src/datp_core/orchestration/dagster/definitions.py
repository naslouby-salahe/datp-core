"""Dagster definitions entrypoint for DATP Core."""

from __future__ import annotations

from dagster import Definitions, ResourceDefinition

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.orchestration.dagster.assets import resolved_project_configuration_asset
from datp_core.orchestration.dagster.resources import DatpConfigurationResource


def build_definitions(config: ResolvedProjectConfiguration) -> Definitions:
    """Build definitions using the composition root's immutable configuration instance."""
    resource = DatpConfigurationResource(config=config)
    return Definitions(
        assets=[resolved_project_configuration_asset],
        resources={"datp_config": ResourceDefinition.hardcoded_resource(resource)},
    )
