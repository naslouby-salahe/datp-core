"""Canonical runtime declaration without scientific overrides."""

from .models import DATA_ROOT, OUTPUTS_ROOT, RESULTS_ROOT, RuntimeProtocol

CANONICAL_RUNTIME = RuntimeProtocol(
    data_root=DATA_ROOT,
    outputs_root=OUTPUTS_ROOT,
    results_root=RESULTS_ROOT,
    require_cuda=False,
    worker_count=1,
    overwrite_outputs=False,
)
