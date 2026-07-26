"""Atomic persistence of already-finalized analysis results.

Holm correction is applied before persistence by the pipeline stage adapter.
This module only serializes and writes — it performs no scientific calculations.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import TypeAdapter

from datp_core.analysis.contracts import AnalysisResult
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.jobs import StageJob


_adapter = TypeAdapter(tuple[AnalysisResult, ...])


def persist_analysis_results(
    *,
    store: ArtifactStore,
    job: StageJob,
    results: Sequence[AnalysisResult],
) -> None:
    """Serialize and atomically persist analysis results using Pydantic.

    *results* must already be finalized (Holm correction, deduplication, etc.).
    """
    payload = _adapter.dump_json(tuple(results))
    store.write_bytes_atomic(job.output_path("statistical_result"), payload)
