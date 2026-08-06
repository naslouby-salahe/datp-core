"""Transactional publication primitive for canonical dataset materialization."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from filelock import FileLock

from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.runtime.filesystem import (
    cleanup_staging_on_failure,
    create_staging_directory,
    remove_stale_staging_directories,
)


@dataclass(frozen=True, slots=True)
class DatasetPublicationOutcome[ValueT]:
    status: PublicationStatus
    value: ValueT
    complete_digest: Checksum


def publish_canonical_atomically[ValueT](
    *,
    target: Path,
    is_reusable: Callable[[Path], bool],
    write: Callable[[Path], ValueT],
    reusable_value: Callable[[Path], ValueT],
    remove_target: Callable[[Path], None] = rmtree,
    complete_marker: str | Path = "COMPLETE",
) -> DatasetPublicationOutcome[ValueT]:
    """Publish one canonical dataset directory without exposing partial state."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(f"{target}.lock"):
        remove_stale_staging_directories(target)
        if is_reusable(target):
            return DatasetPublicationOutcome(
                status=PublicationStatus.REUSED,
                value=reusable_value(target),
                complete_digest=checksum_file(target / complete_marker),
            )
        if target.exists():
            remove_target(target)
        staging = create_staging_directory(target)
        with cleanup_staging_on_failure(staging):
            value = write(staging)
            staging.replace(target)
    return DatasetPublicationOutcome(
        status=PublicationStatus.PUBLISHED,
        value=value,
        complete_digest=checksum_file(target / complete_marker),
    )
