"""Small filesystem primitives shared by every artifact-owning package.

Every package that publishes a directory atomically (pipeline publication,
preprocessing publication, dataset materialization) shares the same staging
lifecycle: create a hidden staging path, write into it, replace the target,
and remove the staging path if anything fails. These primitives are the one
authoritative implementation of that lifecycle.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp


def write_text_atomically(path: Path, content: str, *, encoding: str = "utf-8") -> Path:
    """Replace one text file atomically without exposing a partial destination."""
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


def remove_stale_staging_directories(target: Path) -> None:
    """Remove leftover staging directories left behind by an interrupted publish."""
    parent = target.parent
    if not parent.is_dir():
        return
    prefix = f".{target.name}."
    for candidate in sorted(parent.iterdir()):
        if candidate.is_dir() and candidate.name.startswith(prefix):
            rmtree(candidate, ignore_errors=True)


def create_staging_directory(target: Path) -> Path:
    """Create one hidden staging directory beside a not-yet-published target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))


def replace_directory(staging: Path, target: Path) -> None:
    """Atomically move a staged directory onto its target, replacing any prior contents."""
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
    """Remove every staging path before propagating any failure unchanged."""
    try:
        yield
    except BaseException:
        for path in staging:
            if path.is_dir():
                cleanup_staging_directory(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        raise
