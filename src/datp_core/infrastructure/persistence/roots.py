from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.artifacts.keys import StorageRootSpec
from datp_core.domain.errors import PathResolutionError


@dataclass(frozen=True, slots=True, kw_only=True)
class BoundStorageRoot:
    spec: StorageRootSpec
    absolute_path: Path

    def __post_init__(self) -> None:
        if not self.absolute_path.is_absolute():
            raise PathResolutionError(
                detail="storage root must be an absolute path",
                key=self.spec.kind.value,
                root=str(self.absolute_path),
            )


def bind_storage_root(*, spec: StorageRootSpec, absolute_path: Path) -> BoundStorageRoot:
    return BoundStorageRoot(spec=spec, absolute_path=absolute_path.resolve(strict=False))
