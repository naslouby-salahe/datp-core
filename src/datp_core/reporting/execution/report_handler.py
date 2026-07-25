"""Render reports only from a supplied frozen-result file."""

from __future__ import annotations

from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.reporting.freezing.errors import ResultFreezeError
from datp_core.reporting.rendering.package import render_frozen_report


class ReportGenerationStageHandler:
    stage = StageKind.REPORT_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        try:
            payload = render_frozen_report(self._store.read_bytes(job.input_path("frozen_result")))
            self._store.write_bytes_atomic(job.output_path("report"), payload)
        except (OSError, ResultFreezeError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
