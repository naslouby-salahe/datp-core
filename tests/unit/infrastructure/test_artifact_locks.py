from concurrent.futures import ThreadPoolExecutor
from inspect import signature
from pathlib import Path
from threading import Barrier
from time import sleep

import pytest

from datp_core.application.ports.persistence import (
    AcquireArtifactLockRequest,
    ArtifactLockProvider,
)
from datp_core.domain.artifacts.keys import StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.references import ArtifactId, LockScope
from datp_core.domain.errors import ArtifactLockConflict
from datp_core.infrastructure.persistence.locks import FileArtifactLockLease, FileArtifactLockProvider
from datp_core.infrastructure.persistence.roots import bind_storage_root
from datp_core.infrastructure.runtime.provenance import SystemClock


def _provider(path: Path) -> FileArtifactLockProvider:
    return FileArtifactLockProvider(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
            absolute_path=path,
        ),
        clock=SystemClock(),
    )


def _request(
    owner: str,
    *,
    scope: LockScope = LockScope.COMPUTATION_OWNERSHIP,
    timeout_seconds: int = 1,
    heartbeat_seconds: int | None = None,
) -> AcquireArtifactLockRequest:
    return AcquireArtifactLockRequest(
        artifact_id=ArtifactId(value="artifact-" + "a" * 64),
        owner=owner,
        scope=scope,
        timeout_seconds=timeout_seconds,
        heartbeat_seconds=heartbeat_seconds,
    )


def test_lock_provider_matches_the_port_signature() -> None:
    assert signature(FileArtifactLockProvider.acquire) == signature(ArtifactLockProvider.acquire)


def test_commit_lease_is_released_when_persistence_scope_exits(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    request = _request("commit-writer", scope=LockScope.COMMIT)

    with provider.acquire(request) as lease:
        assert isinstance(lease, FileArtifactLockLease)
        assert lease.owner == "commit-writer"
        assert lease.scope is LockScope.COMMIT
        competing_request = _request("competing-writer", scope=LockScope.COMMIT)

        with pytest.raises(ArtifactLockConflict):
            provider.acquire(competing_request)

    with provider.acquire(_request("next-writer", scope=LockScope.COMMIT)):
        pass


def test_commit_scope_rejects_a_renewable_heartbeat(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    request = _request("commit-writer", scope=LockScope.COMMIT, heartbeat_seconds=1)

    with pytest.raises(ArtifactLockConflict):
        provider.acquire(request)


def test_expired_computation_lease_raises_a_typed_conflict_on_renewal(tmp_path: Path) -> None:
    provider = _provider(tmp_path)

    with provider.acquire(_request("expired-owner", heartbeat_seconds=1)) as lease:
        sleep(1.1)
        with pytest.raises(ArtifactLockConflict):
            lease.renew()
        with pytest.raises(ArtifactLockConflict):
            lease.renew()


def test_explicit_release_ends_the_context_manager_lease(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    lease = provider.acquire(_request("explicit-releaser"))

    lease.release()

    with pytest.raises(ArtifactLockConflict):
        lease.__enter__()
    with provider.acquire(_request("successor")):
        pass


def test_two_truly_concurrent_acquisitions_do_not_both_succeed(tmp_path: Path) -> None:
    barrier = Barrier(2)

    def acquire_concurrently(owner: str) -> bool:
        provider = _provider(tmp_path)
        barrier.wait()
        try:
            with provider.acquire(_request(owner, timeout_seconds=1)):
                sleep(1.1)
                return True
        except ArtifactLockConflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(acquire_concurrently, ("writer-a", "writer-b")))

    assert results.count(True) == 1
    assert results.count(False) == 1


def test_renewal_preserves_an_active_computation_ownership_lease(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    request = _request("long-compute", heartbeat_seconds=1)

    with provider.acquire(request) as lease:
        lease.renew()
        competing_request = _request("competing-compute", timeout_seconds=1)

        with pytest.raises(ArtifactLockConflict):
            provider.acquire(competing_request)
