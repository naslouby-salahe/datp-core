import json
from dataclasses import Field, dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum, StrEnum
from hashlib import sha256
from pathlib import Path
from typing import cast

from datp_core.domain.errors import ConfigurationError


class ProtocolLockVerificationMode(StrEnum):
    REQUIRED = "required"
    SKIP = "skip"


class ProtocolLockStatus(StrEnum):
    VERIFIED = "verified"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtocolLockEntry:
    name: str
    digest: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtocolLockManifest:
    schema_version: str
    hash_algorithm: str
    source_documents: tuple[ProtocolLockEntry, ...]
    resolved_profiles: tuple[ProtocolLockEntry, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtocolLockVerificationResult:
    status: ProtocolLockStatus
    manifest: ProtocolLockManifest | None


def canonical_json(value: object) -> str:
    return json.dumps(_canonical_value(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _canonical_value(value: object) -> object:
    for value_type, mapper in _CANONICAL_VALUE_MAPPERS:
        if isinstance(value, value_type):
            return mapper(cast(object, value))
    return _canonical_dataclass_or_raw(value)


def _canonical_tuple(value: object) -> object:
    return [_canonical_value(item) for item in cast(tuple[object, ...], value)]


def _canonical_list(value: object) -> object:
    return [_canonical_value(item) for item in cast(list[object], value)]


def _canonical_dict(value: object) -> object:
    return {str(key): _canonical_value(item) for key, item in cast(dict[object, object], value).items()}


def _canonical_enum(value: object) -> object:
    return cast(Enum, value).value


def _canonical_decimal(value: object) -> object:
    return str(cast(Decimal, value))


def _canonical_dataclass_or_raw(value: object) -> object:
    if not is_dataclass(value):
        return value
    dataclass_fields = cast(tuple[Field[object], ...], fields(value))
    return {field.name: _canonical_value(cast(object, getattr(value, field.name))) for field in dataclass_fields}


_CANONICAL_VALUE_MAPPERS = (
    (Enum, _canonical_enum),
    (Decimal, _canonical_decimal),
    (tuple, _canonical_tuple),
    (list, _canonical_list),
    (dict, _canonical_dict),
)


def build_protocol_lock_manifest(
    *, source_documents: tuple[tuple[str, str], ...], resolved_profiles: tuple[tuple[str, object], ...]
) -> ProtocolLockManifest:
    return ProtocolLockManifest(
        schema_version="1",
        hash_algorithm="sha256",
        source_documents=tuple(
            ProtocolLockEntry(name=name, digest=_digest(content)) for name, content in sorted(source_documents)
        ),
        resolved_profiles=tuple(
            ProtocolLockEntry(name=name, digest=_digest(canonical_json(value)))
            for name, value in sorted(resolved_profiles, key=lambda item: item[0])
        ),
    )


def verify_protocol_lock(
    *,
    manifest_path: Path,
    source_documents: tuple[tuple[str, str], ...],
    resolved_profiles: tuple[tuple[str, object], ...],
    mode: ProtocolLockVerificationMode,
) -> ProtocolLockVerificationResult:
    if mode is ProtocolLockVerificationMode.SKIP:
        return ProtocolLockVerificationResult(status=ProtocolLockStatus.SKIPPED, manifest=None)
    expected = build_protocol_lock_manifest(source_documents=source_documents, resolved_profiles=resolved_profiles)
    recorded = read_protocol_lock_manifest(path=manifest_path)
    if recorded != expected:
        raise ConfigurationError(
            detail="protocol lock does not match the selected scientific configuration",
            section="locking",
            field=str(manifest_path),
            mode="verify",
        )
    return ProtocolLockVerificationResult(status=ProtocolLockStatus.VERIFIED, manifest=recorded)


def refresh_protocol_lock(
    *,
    manifest_path: Path,
    source_documents: tuple[tuple[str, str], ...],
    resolved_profiles: tuple[tuple[str, object], ...],
) -> ProtocolLockManifest:
    manifest = build_protocol_lock_manifest(source_documents=source_documents, resolved_profiles=resolved_profiles)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    return manifest


def read_protocol_lock_manifest(*, path: Path) -> ProtocolLockManifest:
    raw = _read_protocol_lock_json(path=path)
    return _map_protocol_lock_manifest(raw=raw, path=path)


def _read_protocol_lock_json(*, path: Path) -> dict[str, object]:
    try:
        raw: object = json.loads(  # pyright: ignore[reportUnknownMemberType]
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object
        )
    except FileNotFoundError as error:
        raise ConfigurationError(
            detail="protocol lock manifest is required but missing",
            section="locking",
            field=str(path),
            mode="verify",
        ) from error
    except (json.JSONDecodeError, ValueError) as error:
        raise ConfigurationError(
            detail="protocol lock manifest is malformed",
            section="locking",
            field=str(path),
            mode="verify",
        ) from error
    if not isinstance(raw, dict):
        raise ConfigurationError(
            detail="protocol lock manifest root must be an object",
            section="locking",
            field=str(path),
            mode="verify",
        )
    return cast(dict[str, object], raw)


def _map_protocol_lock_manifest(*, raw: dict[str, object], path: Path) -> ProtocolLockManifest:
    try:
        return ProtocolLockManifest(
            schema_version=_required_text(raw=raw, name="schema_version"),
            hash_algorithm=_required_text(raw=raw, name="hash_algorithm"),
            source_documents=_lock_entries(raw=_required_list(raw=raw, name="source_documents")),
            resolved_profiles=_lock_entries(raw=_required_list(raw=raw, name="resolved_profiles")),
        )
    except ValueError as error:
        raise ConfigurationError(
            detail="protocol lock manifest has an invalid shape",
            section="locking",
            field=str(path),
            mode="verify",
        ) from error


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _required_text(*, raw: dict[str, object], name: str) -> str:
    if name not in raw or type(raw[name]) is not str:
        raise ValueError(name)
    return cast(str, raw[name])


def _required_list(*, raw: dict[str, object], name: str) -> list[object]:
    if name not in raw or type(raw[name]) is not list:
        raise ValueError(name)
    return cast(list[object], raw[name])


def _lock_entries(raw: list[object]) -> tuple[ProtocolLockEntry, ...]:
    entries = tuple(_lock_entry(item=item) for item in raw)
    if not _has_ordered_lock_entries(entries):
        raise ValueError("lock entry ordering")
    return entries


def _lock_entry(*, item: object) -> ProtocolLockEntry:
    if type(item) is not dict:
        raise ValueError("lock entry")
    raw = cast(dict[str, object], item)
    name = _required_text(raw=raw, name="name")
    digest = _required_text(raw=raw, name="digest")
    if len(digest) != 64:
        raise ValueError("digest")
    return ProtocolLockEntry(name=name, digest=digest)


def _has_ordered_lock_entries(entries: tuple[ProtocolLockEntry, ...]) -> bool:
    names = tuple(entry.name for entry in entries)
    return tuple(sorted(names)) == names
