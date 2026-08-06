"""Small filesystem primitives shared by artifact-owning packages."""

from pathlib import Path
from tempfile import NamedTemporaryFile


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
    try:
        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return path
