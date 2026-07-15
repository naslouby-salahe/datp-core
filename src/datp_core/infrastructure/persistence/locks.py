from dataclasses import dataclass
from datetime import UTC, datetime
from os import getpid, kill, replace
from pathlib import Path
from types import TracebackType
from typing import Self
from uuid import uuid4

import msgspec
from filelock import FileLock, Timeout

from datp_core.application.ports.persistence import AcquireArtifactLockRequest, ArtifactLockLease
from datp_core.application.ports.runtime import Clock
from datp_core.domain.artifacts.references import LockScope
from datp_core.domain.errors import ArtifactLockConflict
from datp_core.infrastructure.persistence.roots import BoundStorageRoot


@dataclass(frozen=True, slots=True, kw_only=True)
class _LeaseRecord:
    lease_id: str
    artifact_id: str
    owner: str
    scope: LockScope
    process_id: int
    acquired_at: float
    expires_at: float


@dataclass(slots=True, kw_only=True)
class FileArtifactLockLease:
    request: AcquireArtifactLockRequest
    lock: FileLock
    record_path: Path
    lease_id: str
    owner: str
    scope: LockScope
    clock: Clock
    acquired_at: datetime
    expires_at: datetime
    released: bool = False

    def __enter__(self) -> Self:
        self._require_active()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    def release(self) -> None:
        if self.released:
            return
        try:
            record = _read_record(self.record_path)
            if record is not None and record.lease_id == self.lease_id:
                self.record_path.unlink(missing_ok=True)
        finally:
            self.lock.release()
            self.released = True

    def renew(self) -> None:
        self._require_active()
        heartbeat_seconds = _heartbeat_seconds(self.request)
        record = _read_record(self.record_path)
        now = self.clock.now().timestamp()
        if record is None or not _is_current_record(record, self.lease_id, now):
            self.release()
            raise _conflict(self.request)
        expires_at = now + heartbeat_seconds
        _write_record(
            self.record_path,
            _LeaseRecord(
                lease_id=record.lease_id,
                artifact_id=record.artifact_id,
                owner=record.owner,
                scope=record.scope,
                process_id=record.process_id,
                acquired_at=record.acquired_at,
                expires_at=expires_at,
            ),
        )
        self.expires_at = _timestamp(expires_at)

    def _require_active(self) -> None:
        if self.released:
            raise _conflict(self.request)


@dataclass(frozen=True, slots=True, kw_only=True)
class FileArtifactLockProvider:
    root: BoundStorageRoot
    clock: Clock

    def acquire(self, request: AcquireArtifactLockRequest) -> ArtifactLockLease:
        _validate_request(request)
        lock_directory = self.root.absolute_path / ".artifact-locks"
        lock_directory.mkdir(parents=True, exist_ok=True)
        record_path = lock_directory / f"{request.artifact_id.value}-{request.scope.value}.json"
        lock = FileLock(str(record_path.with_suffix(".lock")))
        _acquire_file_lock(lock, request)
        now = self.clock.now().timestamp()
        try:
            lease_id, expires_at = _claim_lease(request, record_path, now)
        except BaseException:
            lock.release()
            raise
        return FileArtifactLockLease(
            request=request,
            lock=lock,
            record_path=record_path,
            lease_id=lease_id,
            owner=request.owner,
            scope=request.scope,
            clock=self.clock,
            acquired_at=_timestamp(now),
            expires_at=_timestamp(expires_at),
        )


def _validate_request(request: AcquireArtifactLockRequest) -> None:
    if request.timeout_seconds <= 0:
        raise _conflict(request)
    _validate_heartbeat(request)


def _validate_heartbeat(request: AcquireArtifactLockRequest) -> None:
    heartbeat_seconds = request.heartbeat_seconds
    if heartbeat_seconds is not None and heartbeat_seconds <= 0:
        raise _conflict(request)
    if request.scope is LockScope.COMMIT and heartbeat_seconds is not None:
        raise _conflict(request)


def _lease_duration(request: AcquireArtifactLockRequest) -> int:
    return request.heartbeat_seconds if request.heartbeat_seconds is not None else request.timeout_seconds


def _heartbeat_seconds(request: AcquireArtifactLockRequest) -> int:
    if request.scope is LockScope.COMPUTATION_OWNERSHIP and request.heartbeat_seconds is not None:
        return request.heartbeat_seconds
    raise _conflict(request)


def _is_current_record(record: _LeaseRecord, lease_id: str, now: float) -> bool:
    if record.lease_id != lease_id:
        return False
    return record.expires_at > now


def _acquire_file_lock(lock: FileLock, request: AcquireArtifactLockRequest) -> None:
    try:
        lock.acquire(timeout=request.timeout_seconds)
    except Timeout as error:
        raise _conflict(request) from error


def _claim_lease(request: AcquireArtifactLockRequest, record_path: Path, now: float) -> tuple[str, float]:
    existing = _read_record(record_path)
    if _is_live_owner(existing, now):
        raise _conflict(request)
    lease_id = str(uuid4())
    expires_at = now + _lease_duration(request)
    _write_record(
        record_path,
        _LeaseRecord(
            lease_id=lease_id,
            artifact_id=request.artifact_id.value,
            owner=request.owner,
            scope=request.scope,
            process_id=getpid(),
            acquired_at=now,
            expires_at=expires_at,
        ),
    )
    return lease_id, expires_at


def _is_live_owner(record: _LeaseRecord | None, now: float) -> bool:
    if record is None or record.expires_at <= now:
        return False
    return _process_is_alive(record.process_id)


def _read_record(path: Path) -> _LeaseRecord | None:
    if not path.exists():
        return None
    try:
        return msgspec.json.decode(path.read_bytes(), type=_LeaseRecord)
    except (OSError, msgspec.DecodeError, msgspec.ValidationError):
        return None


def _write_record(path: Path, record: _LeaseRecord) -> None:
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_bytes(msgspec.json.encode(record))
    replace(temporary_path, path)


def _process_is_alive(process_id: int) -> bool:
    if process_id <= 0:
        return False
    try:
        kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _timestamp(value: float) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


def _conflict(request: AcquireArtifactLockRequest) -> ArtifactLockConflict:
    return ArtifactLockConflict(
        detail="artifact lock acquisition, renewal, or scope policy conflicted",
        artifact_id=request.artifact_id.value,
        owner=request.owner,
    )
