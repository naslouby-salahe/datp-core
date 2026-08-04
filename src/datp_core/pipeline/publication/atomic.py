"""Atomic directory publication shared by every pipeline branch."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from filelock import FileLock

from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values import Checksum, checksum_file


@dataclass(frozen=True, slots=True)
class PublicationOutcome[ValueT]:
    status: PublicationStatus
    value: ValueT
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class RelatedPublicationOutcome[ValueT]:
    status: PublicationStatus
    value: ValueT


def create_staging_directory(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))


def replace_directory(staging: Path, target: Path) -> None:
    if target.exists():
        rmtree(target)
    staging.replace(target)


def cleanup_staging_directory(staging: Path, *, ignore_errors: bool) -> None:
    if staging.exists():
        rmtree(staging, ignore_errors=ignore_errors)


def publish_atomically[ValueT](
    *,
    target: Path,
    overwrite: bool,
    is_reusable: Callable[[Path], bool],
    write: Callable[[Path], ValueT],
    reusable_value: Callable[[Path], ValueT],
    remove_target: Callable[[Path], None] = rmtree,
    complete_marker: str | Path = "COMPLETE",
) -> PublicationOutcome[ValueT]:
    """Publish one typed value under a lock and return its definitive state."""
    with FileLock(f"{target}.lock"):
        _remove_stale_temporary_directories(target)
        if not overwrite and is_reusable(target):
            return PublicationOutcome(
                status=PublicationStatus.REUSED,
                value=reusable_value(target),
                complete_digest=checksum_file(target / complete_marker),
            )
        if target.exists():
            remove_target(target)
        temporary = create_staging_directory(target)
        try:
            value = write(temporary)
            replace_directory(temporary, target)
        except Exception:
            cleanup_staging_directory(temporary, ignore_errors=True)
            raise
    return PublicationOutcome(
        status=PublicationStatus.PUBLISHED,
        value=value,
        complete_digest=checksum_file(target / complete_marker),
    )


def publish_related_atomically[ValueT](
    *,
    targets: tuple[Path, ...],
    overwrite: bool,
    is_reusable: Callable[[tuple[Path, ...]], bool],
    write: Callable[[tuple[Path, ...]], ValueT],
    reusable_value: Callable[[tuple[Path, ...]], ValueT],
) -> RelatedPublicationOutcome[ValueT]:
    """Commit one logical artifact spanning related directories under one lock."""
    if len(targets) < 2:
        raise ValueError("related publication requires at least two target directories")
    if len(frozenset(targets)) != len(targets):
        raise ValueError("related publication targets must be unique")
    lock_path = targets[0].with_name(f".{targets[0].name}.related.lock")
    with FileLock(str(lock_path)):
        if not overwrite and is_reusable(targets):
            return RelatedPublicationOutcome(
                status=PublicationStatus.REUSED,
                value=reusable_value(targets),
            )
        staging = tuple(create_staging_directory(target) for target in targets)
        backups = tuple(target.with_name(f".{target.name}.backup") for target in targets)
        try:
            value = write(staging)
            _remove_paths(backups)
            for target, backup in zip(targets, backups, strict=True):
                if target.exists():
                    target.replace(backup)
            try:
                for staged, target in zip(staging, targets, strict=True):
                    staged.replace(target)
            except Exception:
                _remove_paths(targets)
                for backup, target in zip(backups, targets, strict=True):
                    if backup.exists():
                        backup.replace(target)
                raise
            _remove_paths(backups)
        except Exception:
            for staged in staging:
                cleanup_staging_directory(staged, ignore_errors=True)
            raise
    return RelatedPublicationOutcome(
        status=PublicationStatus.PUBLISHED,
        value=value,
    )


def _remove_stale_temporary_directories(target: Path) -> None:
    parent = target.parent
    if not parent.is_dir():
        return
    prefix = f".{target.name}."
    for candidate in sorted(parent.iterdir()):
        if candidate.is_dir() and candidate.name.startswith(prefix):
            rmtree(candidate, ignore_errors=True)


def _remove_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.is_dir():
            rmtree(path)
        elif path.exists():
            path.unlink()
