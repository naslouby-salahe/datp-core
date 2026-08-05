"""Executable repository layout and runtime limits."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.values import WorkerCount


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryLayout:
    data_root: Path
    outputs_root: Path
    results_root: Path

    def __post_init__(self) -> None:
        roots = (self.data_root, self.outputs_root, self.results_root)
        if any(root.is_absolute() or not root.parts for root in roots):
            raise ValueError("repository roots must be non-empty project-relative paths")
        if len(set(roots)) != len(roots):
            raise ValueError("repository roots must be distinct")


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeConfiguration:
    layout: RepositoryLayout
    worker_count: WorkerCount


DATA_ROOT = Path("data")
OUTPUTS_ROOT = Path("outputs")
RESULTS_ROOT = Path("results")

CANONICAL_RUNTIME = RuntimeConfiguration(
    layout=RepositoryLayout(
        data_root=DATA_ROOT,
        outputs_root=OUTPUTS_ROOT,
        results_root=RESULTS_ROOT,
    ),
    worker_count=WorkerCount(6),
)
