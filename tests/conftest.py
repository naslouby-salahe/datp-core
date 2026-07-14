import os

import pytest

from tests.support import hypothesis_profiles as hypothesis_profiles


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Refuse, loudly, to collect a CUDA-marked test inside a parallel xdist worker.

    A CUDA test running concurrently with another process on the same GPU is never
    permitted. `PYTEST_XDIST_WORKER` is set by pytest-xdist inside every worker process
    (never in the controller, and never absent an active `-n`/`--numprocesses` run); its
    presence is the reliable signal that this collection is happening under distribution
    — `session.config.option.numprocesses` reads back as unset from inside a worker's own
    view, which is not a usable signal here. `trylast=True` is required: pytest's own
    `-m`/marker-expression deselection is itself a `pytest_collection_modifyitems` hook,
    and without `trylast` this hook can run before that deselection, seeing (and wrongly
    rejecting) a CUDA test that `-m 'not cuda'` was about to filter out anyway. If a
    `cuda`-marked test remains in `items` after all deselection while this env var is
    set, collection is aborted outright rather than letting the test run concurrently
    with whatever else that worker or a sibling worker is executing.
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is None:
        return
    cuda_items = [item.nodeid for item in items if item.get_closest_marker("cuda") is not None]
    if cuda_items:
        raise pytest.UsageError(
            f"CUDA-marked tests were collected inside xdist worker {worker_id!r}: "
            f"{cuda_items}. Run the CUDA lane serialized (no -n flag) instead."
        )
