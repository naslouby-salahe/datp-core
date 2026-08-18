from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp
from typing import Any

from datp_core.core.identifiers import FileContentText


def write_text_atomically(path: Path, content: FileContentText, *, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    with cleanup_staging_on_failure(temporary_path):
        temporary_path.replace(path)
    return path


def stream_text_atomically(path: Path, render: Callable[[Any], None], *, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        render(temporary)
        temporary_path = Path(temporary.name)
    with cleanup_staging_on_failure(temporary_path):
        temporary_path.replace(path)
    return path


def remove_stale_staging_directories(target: Path) -> None:
    parent = target.parent
    if not parent.is_dir():
        return
    prefix = f".{target.name}."
    for candidate in sorted(parent.iterdir()):
        if candidate.is_dir() and candidate.name.startswith(prefix):
            rmtree(candidate, ignore_errors=True)


def create_staging_directory(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))


def replace_directory(staging: Path, target: Path) -> None:
    if target.exists():
        rmtree(target)
    staging.replace(target)


def cleanup_staging_directory(staging: Path, *, ignore_errors: bool = True) -> None:
    if staging.exists():
        rmtree(staging, ignore_errors=ignore_errors)


def remove_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.is_dir():
            rmtree(path)
        elif path.exists():
            path.unlink()


@contextmanager
def cleanup_staging_on_failure(*staging: Path) -> Generator[None]:
    try:
        yield
    except BaseException:
        for path in staging:
            if path.is_dir():
                cleanup_staging_directory(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        raise
