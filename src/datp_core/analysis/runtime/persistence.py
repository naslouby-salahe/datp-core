"""Atomic persistence of already-finalized analysis results.

Holm correction is applied before persistence by the pipeline stage adapter.
This module only encodes and writes — it performs no scientific calculations.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from datp_core.analysis.contracts import AnalysisResultContract
from datp_core.analysis.runtime.codec import encode_analysis_result
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.jobs import StageJob


def persist_analysis_results(
    *,
    store: ArtifactStore,
    job: StageJob,
    results: Sequence[AnalysisResultContract],
) -> None:
    """Encode and atomically persist analysis results.

    *results* must already be finalized (Holm correction, deduplication, etc.).
    """
    envelopes = [encode_analysis_result(result) for result in results]
    dict_envelopes = [
        {
            "result_kind": env.result_kind.value,
            "payload_version": env.payload_version,
            "data": env.data,
        }
        for env in envelopes
    ]
    payload = json.dumps(
        dict_envelopes,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    store.write_bytes_atomic(job.output_path("statistical_result"), payload)
