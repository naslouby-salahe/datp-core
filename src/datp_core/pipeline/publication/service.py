"""Artifact codecs, atomic staging, completion, and reload validation."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp
from typing import Protocol

from filelock import FileLock
from pydantic import BaseModel

from datp_core.domain.enums import PublicationStatus
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_file, checksum_text
from datp_core.domain.values.counts import ByteCount
from datp_core.pipeline.publication.models import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactState,
    CompletionRecord,
    CompletionState,
)

COMPLETION_RECORD_ASSET = "completion.json"


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


class ArtifactCodec[RequestT, ResultT](Protocol):
    def write(self, request: RequestT, directory: Path) -> ResultT: ...

    def validate(self, request: RequestT, directory: Path) -> bool: ...

    def load(self, request: RequestT, directory: Path) -> ResultT: ...

    def rebase(self, result: ResultT, directory: Path) -> ResultT: ...


class RelatedArtifactCodec[RequestT, ResultT](Protocol):
    def write(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT: ...

    def validate(self, request: RequestT, directories: tuple[Path, ...]) -> bool: ...

    def load(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT: ...

    def rebase(self, result: ResultT, directories: tuple[Path, ...]) -> ResultT: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionalArtifactCodec[RequestT, ResultT]:
    """Callable-backed codec used by thin orchestration adapters."""

    writer: Callable[[RequestT, Path], ResultT]
    validator: Callable[[RequestT, Path], bool]
    loader: Callable[[RequestT, Path], ResultT]
    rebaser: Callable[[ResultT, Path], ResultT]

    def write(self, request: RequestT, directory: Path) -> ResultT:
        return self.writer(request, directory)

    def validate(self, request: RequestT, directory: Path) -> bool:
        return self.validator(request, directory)

    def load(self, request: RequestT, directory: Path) -> ResultT:
        return self.loader(request, directory)

    def rebase(self, result: ResultT, directory: Path) -> ResultT:
        return self.rebaser(result, directory)


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionalRelatedArtifactCodec[RequestT, ResultT]:
    """Callable-backed related-directory codec used by orchestration adapters."""

    writer: Callable[[RequestT, tuple[Path, ...]], ResultT]
    validator: Callable[[RequestT, tuple[Path, ...]], bool]
    loader: Callable[[RequestT, tuple[Path, ...]], ResultT]
    rebaser: Callable[[ResultT, tuple[Path, ...]], ResultT]

    def write(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT:
        return self.writer(request, directories)

    def validate(self, request: RequestT, directories: tuple[Path, ...]) -> bool:
        return self.validator(request, directories)

    def load(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT:
        return self.loader(request, directories)

    def rebase(self, result: ResultT, directories: tuple[Path, ...]) -> ResultT:
        return self.rebaser(result, directories)


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactPublication[RequestT, ResultT]:
    target: Path
    request: RequestT
    codec: ArtifactCodec[RequestT, ResultT]
    overwrite: bool
    complete_marker: str | Path = "COMPLETE"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactPublicationResult[ResultT]:
    status: PublicationStatus
    value: ResultT
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedPublicationMember:
    identity: str
    target: Path

    def __post_init__(self) -> None:
        if not self.identity:
            raise ValueError("related publication member identity must be non-empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedArtifactPublication[RequestT, ResultT]:
    request: RequestT
    members: tuple[RelatedPublicationMember, ...]
    codec: RelatedArtifactCodec[RequestT, ResultT]
    overwrite: bool

    def __post_init__(self) -> None:
        if len(self.members) < 2:
            raise ValueError("related artifact publication requires at least two members")
        identities = tuple(member.identity for member in self.members)
        targets = tuple(member.target for member in self.members)
        if len(frozenset(identities)) != len(identities):
            raise ValueError("related publication member identities must be unique")
        if len(frozenset(targets)) != len(targets):
            raise ValueError("related publication targets must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedArtifactPublicationResult[ResultT]:
    status: PublicationStatus
    value: ResultT


def publish_artifact[RequestT, ResultT](
    publication: ArtifactPublication[RequestT, ResultT],
) -> ArtifactPublicationResult[ResultT]:
    """Execute the common artifact lifecycle exactly once for every feature codec."""
    codec = publication.codec
    request = publication.request
    outcome = publish_atomically(
        target=publication.target,
        overwrite=publication.overwrite,
        is_reusable=lambda directory: codec.validate(request, directory),
        write=lambda directory: codec.write(request, directory),
        reusable_value=lambda directory: codec.load(request, directory),
        complete_marker=publication.complete_marker,
    )
    return ArtifactPublicationResult(
        status=outcome.status,
        value=codec.rebase(outcome.value, publication.target),
        complete_digest=outcome.complete_digest,
    )


def publish_related_artifacts[RequestT, ResultT](
    publication: RelatedArtifactPublication[RequestT, ResultT],
) -> RelatedArtifactPublicationResult[ResultT]:
    """Execute one transactional lifecycle for a related-directory artifact."""
    codec = publication.codec
    request = publication.request
    targets = tuple(member.target for member in publication.members)
    outcome = publish_related_atomically(
        targets=targets,
        overwrite=publication.overwrite,
        is_reusable=lambda directories: codec.validate(request, directories),
        write=lambda directories: codec.write(request, directories),
        reusable_value=lambda directories: codec.load(request, directories),
    )
    return RelatedArtifactPublicationResult(
        status=outcome.status,
        value=codec.rebase(outcome.value, targets),
    )


def complete_digest(manifest_payload: str, schema_payload: str) -> Checksum:
    """Bind a manifest and schema payload into one deterministic completion digest."""
    return checksum_text(f"{manifest_payload}\n{schema_payload}")


def build_completion_record(
    *,
    plan_digest: Checksum | str,
    campaign_digest: Checksum | str,
    artifacts: tuple[ArtifactRecord, ...],
) -> CompletionRecord:
    state = (
        CompletionState.COMPLETE
        if artifacts and all(item.state is ArtifactState.PUBLISHED for item in artifacts)
        else CompletionState.INCOMPLETE
    )
    return CompletionRecord(
        plan_digest=plan_digest if isinstance(plan_digest, Checksum) else Checksum(plan_digest),
        campaign_digest=campaign_digest if isinstance(campaign_digest, Checksum) else Checksum(campaign_digest),
        artifacts=artifacts,
        state=state,
    )


def require_complete(record: CompletionRecord) -> None:
    if record.state is not CompletionState.COMPLETE:
        raise ValueError("experiment publication is incomplete")
    invalid = tuple(item for item in record.artifacts if item.state is not ArtifactState.PUBLISHED)
    if invalid:
        raise ValueError("experiment publication contains non-published artifacts")


def write_completion_record(directory: Path, record: CompletionRecord) -> Path:
    """Persist one completion record as canonical JSON. Artifact paths are recorded
    exactly as given (typically relative to a shared output root, not this directory,
    so reusable assets are referenced rather than copied)."""
    payload = {
        "plan_digest": record.plan_digest.value,
        "campaign_digest": record.campaign_digest.value,
        "state": record.state.value,
        "artifacts": [
            {
                "kind": item.kind.value,
                "relative_path": item.relative_path.as_posix(),
                "checksum": item.checksum.value,
                "byte_count": item.byte_count.value,
                "state": item.state.value,
            }
            for item in record.artifacts
        ],
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / COMPLETION_RECORD_ASSET
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return path


def read_completion_record(directory: Path) -> CompletionRecord | None:
    """Reload one completion record, or None if absent, unreadable, or structurally invalid."""
    path = directory / COMPLETION_RECORD_ASSET
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CompletionRecord(
            plan_digest=Checksum(payload["plan_digest"]),
            campaign_digest=Checksum(payload["campaign_digest"]),
            state=CompletionState(payload["state"]),
            artifacts=tuple(
                ArtifactRecord(
                    kind=ArtifactKind(item["kind"]),
                    relative_path=Path(item["relative_path"]),
                    checksum=Checksum(item["checksum"]),
                    byte_count=ByteCount(item["byte_count"]),
                    state=ArtifactState(item["state"]),
                )
                for item in payload["artifacts"]
            ),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReloadValidation:
    valid: bool
    evidence: tuple[str, ...]


def validate_reload(
    *,
    root: Path,
    completion: CompletionRecord,
    observed: tuple[ArtifactRecord, ...],
) -> ReloadValidation:
    evidence: list[str] = []
    expected_paths = tuple(item.relative_path for item in completion.artifacts)
    observed_paths = tuple(item.relative_path for item in observed)
    if not completion.complete:
        evidence.append("completion marker is not complete")
    if expected_paths != observed_paths:
        evidence.append("observed artifact ordering or membership differs from the completion record")
    expected_by_path = tuple((item.relative_path, item.checksum, item.byte_count) for item in completion.artifacts)
    observed_by_path = tuple((item.relative_path, item.checksum, item.byte_count) for item in observed)
    if expected_by_path != observed_by_path:
        evidence.append("artifact checksum or byte-count metadata mismatch")
    if any(item.state is not ArtifactState.PUBLISHED for item in observed):
        evidence.append("observed publication contains a non-published artifact")

    for artifact in completion.artifacts:
        artifact_path = root / artifact.relative_path
        if not artifact_path.is_file():
            evidence.append(f"completed artifact is absent: {artifact.relative_path.as_posix()}")
            continue
        actual_checksum = checksum_file(artifact_path)
        if actual_checksum != artifact.checksum:
            evidence.append(f"artifact checksum mismatch: {artifact.relative_path.as_posix()}")
        if artifact_path.stat().st_size != artifact.byte_count.value:
            evidence.append(f"artifact byte-count mismatch: {artifact.relative_path.as_posix()}")

    return ReloadValidation(valid=not evidence, evidence=tuple(evidence))


def canonical_model_json_text(model: BaseModel) -> str:
    return canonical_json_text(model)


def serialize_json_model(model: BaseModel, destination: Path) -> Checksum:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_text(model)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file.write(payload)
        temporary_path = Path(temporary_file.name)
    try:
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return checksum_text(payload)


def load_model_json[ModelT: BaseModel](model_type: type[ModelT], text: str) -> ModelT:
    return model_type.model_validate_json(text)


def load_model_file[ModelT: BaseModel](model_type: type[ModelT], path: Path) -> ModelT:
    return load_model_json(model_type, path.read_text(encoding="utf-8"))
