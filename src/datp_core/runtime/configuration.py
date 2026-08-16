from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryLayout:
    data_root: Path
    outputs_root: Path
    results_root: Path

    def __post_init__(self) -> None:
        roots = (self.data_root, self.outputs_root, self.results_root)
        if any(root.is_absolute() or not root.parts for root in roots):
            raise ValueError("repository roots must be non-empty project-relative paths")
        if len(frozenset(roots)) != len(roots):
            raise ValueError("repository roots must be distinct")


REPOSITORY_LAYOUT = RepositoryLayout(
    data_root=Path("data"),
    outputs_root=Path("outputs"),
    results_root=Path("results"),
)

DATA_ROOT = REPOSITORY_LAYOUT.data_root
OUTPUTS_ROOT = REPOSITORY_LAYOUT.outputs_root
RESULTS_ROOT = REPOSITORY_LAYOUT.results_root
