"""Environment and bootstrap runtime settings using pydantic-settings and single resolved paths authority."""

from __future__ import annotations

from pathlib import Path

from attrs import define
from pydantic import Field, JsonValue
from pydantic_settings import BaseSettings, SettingsConfigDict

from datp_core.config.models.runtime_config import AuthoredRuntimeConfig


class RuntimeBootstrapSettings(BaseSettings):
    """External bootstrap settings that cannot be authored in repository YAML."""

    model_config = SettingsConfigDict(
        env_prefix="DATP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    repository_root: Path = Field(default_factory=lambda: Path.cwd().resolve())
    config_root: Path = Field(default_factory=lambda: Path("configs").resolve())
    dagster_home: Path | None = None
    environment_identity: str = "local_linux"


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProjectPaths:
    """Immutable resolved project paths resolved once at bootstrap time."""

    repository_root: Path
    config_root: Path
    raw_data: Path
    processed_data: Path
    manifests: Path
    checkpoints: Path
    outputs: Path
    runtime_state: Path

    def __attrs_post_init__(self) -> None:
        if not self.repository_root.is_absolute():
            raise ValueError(f"Repository root must be absolute: {self.repository_root}")
        if not self.config_root.is_absolute():
            raise ValueError(f"Config root must be absolute: {self.config_root}")


@define(frozen=True, slots=True, kw_only=True)
class ResolvedRuntimeConfiguration:
    """Fully resolved runtime configuration combining bootstrap settings and runtime.yaml."""

    bootstrap: RuntimeBootstrapSettings
    paths: ResolvedProjectPaths
    raw_source_policy: dict[str, JsonValue]
    determinism_enforcement: dict[str, JsonValue]
    device_policy_rules: dict[str, JsonValue]
    resource_pressure_policy: dict[str, JsonValue]
    execution_profiles: dict[str, JsonValue]


def resolve_runtime_configuration(
    authored_runtime: AuthoredRuntimeConfig,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedRuntimeConfiguration:
    """Resolve runtime paths and configuration once during composition."""
    settings = bootstrap_settings or RuntimeBootstrapSettings()
    repo_root = settings.repository_root.resolve()
    config_root = (
        (repo_root / settings.config_root).resolve()
        if not settings.config_root.is_absolute()
        else settings.config_root.resolve()
    )

    roots = authored_runtime.roots
    resolved_paths = ResolvedProjectPaths(
        repository_root=repo_root,
        config_root=config_root,
        raw_data=(repo_root / roots["raw_data"]).resolve(),
        processed_data=(repo_root / roots["processed_data"]).resolve(),
        manifests=(repo_root / roots["manifests"]).resolve(),
        checkpoints=(repo_root / roots["checkpoints"]).resolve(),
        outputs=(repo_root / roots["outputs"]).resolve(),
        runtime_state=(repo_root / roots["runtime_state"]).resolve(),
    )

    return ResolvedRuntimeConfiguration(
        bootstrap=settings,
        paths=resolved_paths,
        raw_source_policy=authored_runtime.raw_source_policy.model_dump(),
        determinism_enforcement=authored_runtime.determinism_enforcement.model_dump(),
        device_policy_rules=authored_runtime.device_policy_rules.model_dump(),
        resource_pressure_policy=authored_runtime.resource_pressure_policy.model_dump(),
        execution_profiles={k: v.model_dump() for k, v in authored_runtime.execution_profiles.items()},
    )
