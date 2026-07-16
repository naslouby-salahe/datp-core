from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path

from blake3 import blake3
# TODO - Move these constants to a configuration file 
DEFAULT_HASH_CHUNK_SIZE = 1024 * 1024


def blake3_bytes_content_hash(content: bytes) -> str:
    return blake3(content).hexdigest()


def blake3_chunks_content_hash(chunks: Iterable[bytes]) -> str:
    hasher = blake3()
    for chunk in chunks:
        hasher.update(chunk)
    return hasher.hexdigest()


def blake3_file_content_hash(path: Path, *, chunk_size: int = DEFAULT_HASH_CHUNK_SIZE) -> str:
    return blake3_chunks_content_hash(_file_chunks(path=path, chunk_size=chunk_size))


def sha256_bytes_content_hash(content: bytes) -> str:
    return sha256(content).hexdigest()


def sha256_file_content_hash(path: Path, *, chunk_size: int = DEFAULT_HASH_CHUNK_SIZE) -> str:
    hasher = sha256()
    for chunk in _file_chunks(path=path, chunk_size=chunk_size):
        hasher.update(chunk)
    return hasher.hexdigest()


def _file_chunks(*, path: Path, chunk_size: int) -> Iterable[bytes]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    with path.open("rb") as content_file:
        while chunk := content_file.read(chunk_size):
            yield chunk
