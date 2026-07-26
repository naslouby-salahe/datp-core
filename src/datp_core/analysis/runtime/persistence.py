"""Atomic persistence of already-finalized analysis results.

Holm correction is applied before persistence by the pipeline handler.
This module only encodes and writes — it performs no scientific calculations.
"""

from __future__ import annotations

import json

from datp_core.analysis.runtime.codec import unstructure_analysis_result
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.jobs import StageJob


def persist_analysis_results(
    *,
    store: ArtifactStore,
    job: StageJob,
    results: list,
) -> None:
    """Encode and atomically persist analysis results.

    *results* must already be finalized (Holm correction, deduplication, etc.).
    """
    payload = json.dumps(
        [unstructure_analysis_result(result) for result in results],
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    store.write_bytes_atomic(job.output_path("statistical_result"), payload)
