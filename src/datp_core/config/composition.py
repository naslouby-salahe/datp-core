"""Hydra-backed configuration composition boundary.

Loads the six canonical YAML files, composes them into one tree using OmegaConf,
applies Hydra-style overrides, resolves interpolations, validates through the
existing authored Pydantic models, and delegates to the shared resolution pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from omegaconf import DictConfig, OmegaConf

from datp_core.config.authored.datasets import AuthoredDatasetConfig
from datp_core.config.authored.experiments import AuthoredExperimentsCatalogueConfig
from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.authored.runtime import AuthoredRuntimeConfig
from datp_core.config.bootstrap import RuntimeBootstrapSettings
from datp_core.config.errors import ConfigurationError
from datp_core.config.models import ResolvedProjectConfiguration
from datp_core.config.project import resolve_from_authored_documents
from datp_core.config.validation.project import ProjectConfigurationValidator


def compose_project_config(
    config_root: Path,
    *,
    overrides: list[str] | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedProjectConfiguration:
    """Load the six canonical YAML files, compose with OmegaConf, apply overrides, resolve, validate.

    ``OmegaConf`` types (``DictConfig``, ``ListConfig``) are an internal implementation detail
    and never leave this function -- callers receive a purely Pydantic-validated result.

    Parameters
    ----------
    config_root:
        Path to the ``configs/`` directory containing ``experiments.yaml``,
        ``protocols.yaml``, ``runtime.yaml``, and the ``datasets/`` subdirectory.
    overrides:
        Hydra-style dotlist overrides such as
        ``["runtime.execution_profiles.smoke.resource_budget.max_ram_gib=4"]``.
    bootstrap_settings:
        Optional bootstrap settings.  When ``None``, environment-based discovery
        (``DATP_REPOSITORY_ROOT``, ``DATP_EXECUTION_PROFILE``) is used.

    Returns
    -------
    Immutable resolved project configuration with cross-document guards applied.

    Raises
    ------
    ConfigurationError
        If any file is missing, contains invalid YAML, fails authored-model
        validation, or violates cross-document scientific guards.
    """
    # 1. Load and compose the six YAML files into a single OmegaConf tree
    cfg = _load_and_compose(config_root)

    # 2. Apply Hydra-style dotlist overrides
    if overrides:
        override_cfg = OmegaConf.from_dotlist(overrides)
        cfg = OmegaConf.merge(cfg, override_cfg)

    # 3. Resolve interpolations (e.g. ``${...}`` references)
    OmegaConf.resolve(cfg)

    # 4. Convert to plain Python containers -- OmegaConf types stop here.
    #    cast() is necessary because OmegaConf's type stub returns a broad union;
    #    the isinstance check guarantees we have a dict at this point.
    raw = cast("dict[str, object]", OmegaConf.to_container(cfg, resolve=True))
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Composed configuration root must be a mapping, got {type(raw).__name__}")

    # 5. Validate each composed section through its authored Pydantic model
    documents = _parse_authored_sections(raw)

    # 6. Run the shared resolution pipeline (per-document resolution + fingerprinting + assembly)
    resolved = resolve_from_authored_documents(
        authored_datasets=documents.datasets,
        authored_experiments=documents.experiments,
        authored_protocols=documents.protocols,
        authored_runtime=documents.runtime,
        bootstrap_settings=bootstrap_settings or RuntimeBootstrapSettings(),  # pyright: ignore[reportCallIssue]
    )

    # 7. Cross-document scientific guard validation
    validation_report = ProjectConfigurationValidator().validate(resolved)
    if not validation_report.is_valid:
        raise ConfigurationError(f"Resolved configuration violates scientific guards: {validation_report.errors}")

    return resolved


def _load_and_compose(config_root: Path) -> DictConfig:
    """Load the six canonical YAML files into a single OmegaConf ``DictConfig`` tree.

    The resulting tree structure::

        datasets
          nbaiot
          ciciot2023
          edge_iiotset
        experiments
        protocols
        runtime
    """
    datasets_dir = config_root / "datasets"
    if not datasets_dir.is_dir():
        raise ConfigurationError(
            f"Datasets directory does not exist or is not a directory: {datasets_dir}",
            source_path=datasets_dir,
        )

    datasets: dict[str, DictConfig] = {}
    for ds_path in sorted(datasets_dir.glob("*.yaml")):
        ds_name = ds_path.stem
        loaded = OmegaConf.load(ds_path)
        if not isinstance(loaded, DictConfig):
            raise ConfigurationError(
                f"Dataset YAML must resolve to a mapping, got {type(loaded).__name__}",
                source_path=ds_path,
            )
        datasets[ds_name] = loaded

    experiments_path = config_root / "experiments.yaml"
    protocols_path = config_root / "protocols.yaml"
    runtime_path = config_root / "runtime.yaml"

    for path, name in [
        (experiments_path, "experiments.yaml"),
        (protocols_path, "protocols.yaml"),
        (runtime_path, "runtime.yaml"),
    ]:
        if not path.is_file():
            raise ConfigurationError(
                f"Required configuration file not found: {name}",
                source_path=path,
            )

    return OmegaConf.create(
        {
            "datasets": datasets,
            "experiments": OmegaConf.load(experiments_path),
            "protocols": OmegaConf.load(protocols_path),
            "runtime": OmegaConf.load(runtime_path),
        }
    )


def _parse_authored_sections(
    raw: dict[str, object],
) -> _AuthoredDocuments:
    """Convert the composed raw dict into validated authored Pydantic models.

    Each top-level key (``datasets``, ``experiments``, ``protocols``, ``runtime``)
    is validated through its canonical authored schema.
    """
    datasets_raw = raw.get("datasets")
    experiments_raw = raw.get("experiments")
    protocols_raw = raw.get("protocols")
    runtime_raw = raw.get("runtime")

    if not isinstance(datasets_raw, dict):
        raise ConfigurationError("Composed configuration 'datasets' section must be a mapping")
    if not isinstance(experiments_raw, dict):
        raise ConfigurationError("Composed configuration 'experiments' section must be a mapping")
    if not isinstance(protocols_raw, dict):
        raise ConfigurationError("Composed configuration 'protocols' section must be a mapping")
    if not isinstance(runtime_raw, dict):
        raise ConfigurationError("Composed configuration 'runtime' section must be a mapping")

    authored_datasets = tuple(AuthoredDatasetConfig.model_validate(ds_data) for ds_data in datasets_raw.values())
    authored_experiments = AuthoredExperimentsCatalogueConfig.model_validate(experiments_raw)
    authored_protocols = AuthoredProtocolsConfig.model_validate(protocols_raw)
    authored_runtime = AuthoredRuntimeConfig.model_validate(runtime_raw)

    return _AuthoredDocuments(
        datasets=authored_datasets,
        experiments=authored_experiments,
        protocols=authored_protocols,
        runtime=authored_runtime,
    )


class _AuthoredDocuments:
    """Private container for the four authored document groups after Pydantic validation.

    Avoids returning a bare tuple and keeps the parsing boundary explicit.
    """

    __slots__ = ("datasets", "experiments", "protocols", "runtime")

    def __init__(
        self,
        datasets: tuple[AuthoredDatasetConfig, ...],
        experiments: AuthoredExperimentsCatalogueConfig,
        protocols: AuthoredProtocolsConfig,
        runtime: AuthoredRuntimeConfig,
    ) -> None:
        self.datasets = datasets
        self.experiments = experiments
        self.protocols = protocols
        self.runtime = runtime
