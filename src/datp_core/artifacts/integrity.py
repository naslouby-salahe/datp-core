from hashlib import sha256
from pathlib import Path

from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage
from datp_core.core.identifiers import ContractSubject, NonEmptyString


class ArtifactDigest(NonEmptyString):
    validation_name = "artifact digest"


def artifact_byte_count(path: Path) -> int:
    if not path.is_file():
        raise ArtifactIntegrityError(
            ErrorMessage(f"artifact is not a regular file: {path}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return path.stat().st_size


def artifact_digest(path: Path) -> ArtifactDigest:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return ArtifactDigest(digest.hexdigest())


def require_nonempty_file(path: Path) -> None:
    if not path.is_file():
        raise ArtifactIntegrityError(
            ErrorMessage(f"required artifact is missing: {path}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if artifact_byte_count(path) == 0:
        raise ArtifactIntegrityError(
            ErrorMessage(f"required artifact is empty: {path}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
