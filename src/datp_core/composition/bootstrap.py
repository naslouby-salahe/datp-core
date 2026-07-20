"""Application composition; no scientific formulas or YAML traversal live here."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..artifacts.filesystem import FilesystemArtifactStore
from ..catalogue.domain import ResolvedConfiguration
from ..catalogue.services import load_resolved_configuration
from ..datasets.adapters import Ciciot2023Adapter, EdgeIiotsetAdapter
from ..datasets.adapters.nbaiot import NBaIoTAdapter
from ..datasets.services import DatasetAdapterRegistry


@dataclass(frozen=True, slots=True, kw_only=True)
class Application:
    configuration: ResolvedConfiguration
    artifacts: FilesystemArtifactStore
    dataset_adapters: DatasetAdapterRegistry


def bootstrap(root: Path) -> Application:
    configuration = load_resolved_configuration(root)
    artifacts_root = root / str(configuration.runtime.roots["manifests"])
    dataset_adapters = DatasetAdapterRegistry(
        adapters={
            NBaIoTAdapter().dataset_id: NBaIoTAdapter(),
            Ciciot2023Adapter().dataset_id: Ciciot2023Adapter(),
            EdgeIiotsetAdapter().dataset_id: EdgeIiotsetAdapter(),
        }
    )
    return Application(
        configuration=configuration,
        artifacts=FilesystemArtifactStore(artifacts_root),
        dataset_adapters=dataset_adapters,
    )
