from multiprocessing import get_context
from multiprocessing.synchronize import Event as ProcessEvent
from os import _exit
from pathlib import Path
from time import sleep

import pytest

from datp_core.application.ports.persistence import AcquireArtifactLockRequest
from datp_core.domain.artifacts.keys import StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.references import ArtifactId, LockScope
from datp_core.domain.errors import ArtifactLockConflict
from datp_core.infrastructure.persistence.locks import FileArtifactLockProvider
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


def _request(owner: str, *, heartbeat_seconds: int | None = None) -> AcquireArtifactLockRequest:
    return AcquireArtifactLockRequest(
        artifact_id=ArtifactId(value="artifact-" + "b" * 64),
        owner=owner,
        scope=LockScope.COMPUTATION_OWNERSHIP,
        timeout_seconds=1,
        heartbeat_seconds=heartbeat_seconds,
    )


def _die_while_holding_lock(root: str) -> None:
    _provider(Path(root)).acquire(_request("dead-owner", heartbeat_seconds=1))
    _exit(0)


def _hold_live_lock(root: str, ready: ProcessEvent) -> None:
    with _provider(Path(root)).acquire(_request("slow-but-alive", heartbeat_seconds=2)):
        ready.set()
        sleep(1.5)


def test_expired_dead_owner_record_is_reclaimed_after_process_death(tmp_path: Path) -> None:
    context = get_context("spawn")
    owner = context.Process(target=_die_while_holding_lock, args=(str(tmp_path),))
    owner.start()
    owner.join(timeout=5)
    assert owner.exitcode == 0

    with _provider(tmp_path).acquire(_request("reclaimer", heartbeat_seconds=1)):
        pass


def test_synthetic_writer_releases_its_lease_for_a_successor(tmp_path: Path) -> None:
    provider = _provider(tmp_path)

    with provider.acquire(_request("first-writer")):
        pass
    with provider.acquire(_request("second-writer")):
        pass


def test_heartbeat_renewal_retains_a_synthetic_writer_lease(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    contending_request = _request("contending-writer")

    with provider.acquire(_request("heartbeat-owner", heartbeat_seconds=1)) as lease:
        lease.renew()
        with pytest.raises(ArtifactLockConflict):
            provider.acquire(contending_request)


def test_slow_but_alive_owner_is_not_reclaimed_as_stale(tmp_path: Path) -> None:
    context = get_context("spawn")
    ready = context.Event()
    owner = context.Process(target=_hold_live_lock, args=(str(tmp_path), ready))
    owner.start()
    assert ready.wait(timeout=5)
    premature_reclaimer = _provider(tmp_path)
    reclaimer_request = _request("premature-reclaimer", heartbeat_seconds=1)

    with pytest.raises(ArtifactLockConflict):
        premature_reclaimer.acquire(reclaimer_request)

    owner.join(timeout=5)
    assert owner.exitcode == 0
