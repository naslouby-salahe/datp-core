"""Canonical runtime declaration without scientific overrides."""

from pathlib import Path

from datp_core.domain.values import WorkerCount

from .models import RuntimeProtocol

DATA_ROOT = Path("data")
OUTPUTS_ROOT = Path("outputs")
RESULTS_ROOT = Path("results")

CANONICAL_RUNTIME = RuntimeProtocol(
    data_root=DATA_ROOT,
    outputs_root=OUTPUTS_ROOT,
    results_root=RESULTS_ROOT,
    require_cuda=True,
    worker_count=WorkerCount(6),
    overwrite_outputs=False,
)
