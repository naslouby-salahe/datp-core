"""Dagster resources composed from the one already-resolved project configuration."""

from __future__ import annotations

from attrs import define

from datp_core.config.resolver import ResolvedProjectConfiguration


@define(frozen=True, slots=True)
class DatpConfigurationResource:
    """Runtime resource that never reloads configuration during an orchestration run."""

    config: ResolvedProjectConfiguration

    def get_resolved_config(self) -> ResolvedProjectConfiguration:
        return self.config
