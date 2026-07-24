"""Result ordering, Holm correction, JSON serialization, and artifact commit for the persisted
statistical-analysis artifact."""

from __future__ import annotations

import json
from typing import cast

from attrs import evolve

from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.result import AnalysisResult, analysis_result_to_payload
from datp_core.analysis.statistics.multiplicity import holm_adjust_p_values
from datp_core.artifacts.identity import ArtifactFormat
from datp_core.core.identifiers import ExperimentId
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.models import ArtifactCommitResult
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import node_path


def apply_holm_correction(results: list[AnalysisResult]) -> list[AnalysisResult]:
    """Apply the Holm-Bonferroni correction across every paired-threshold analysis' p-value."""
    candidates: list[tuple[int, float]] = [
        (index, result.p_value)
        for index, result in enumerate(results)
        if isinstance(result, PairedThresholdAnalysisResult) and result.p_value is not None
    ]
    if len(candidates) < 2:
        return results
    adjusted = holm_adjust_p_values(value for _, value in candidates)
    updated = list(results)
    for (index, _), adjusted_value in zip(candidates, adjusted, strict=True):
        updated[index] = evolve(
            cast(PairedThresholdAnalysisResult, updated[index]), holm_adjusted_p_value=adjusted_value
        )
    return updated


def persist_analysis_results(
    *,
    repository: ArtifactRepository,
    config: ResolvedProjectConfiguration,
    job: StageJob,
    experiment_id: ExperimentId,
    results: list[AnalysisResult],
) -> ArtifactCommitResult:
    relative_path = node_path(job.node_key)
    payload = json.dumps(
        [analysis_result_to_payload(result) for result in apply_holm_correction(results)],
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return commit_artifact(
        repository,
        config,
        job.context,
        artifact_key=job.output,
        artifact_format=ArtifactFormat.JSON,
        relative_path=relative_path,
        parents=artifact_parents(
            config,
            tuple(
                (input_key, node_path(dependency))
                for input_key, dependency in zip(job.inputs, job.dependencies, strict=True)
            ),
        ),
        payload=BytesPayload(payload_bytes=payload),
    )


__all__ = ["apply_holm_correction", "persist_analysis_results"]
