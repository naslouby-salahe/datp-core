"""Runtime declaration constants without scientific overrides."""

from pathlib import Path

from .models import RuntimeProtocol

DEFAULT_RUNTIME = RuntimeProtocol(
    data_root=Path("data"), outputs_root=Path("outputs"), require_cuda=False, worker_count=1, overwrite_outputs=False
)
