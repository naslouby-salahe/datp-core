"""Pipeline stage for report generation."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactFormat
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.experiments.identity import IdentityBuilder
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import node_path
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.reporting.freezing.errors import ResultFreezeError
from datp_core.reporting.rendering.package import render_frozen_report


class ReportGenerationStageHandler:
    """Render configured report artifacts exclusively from a frozen result manifest."""

    stage = StageKind.REPORT_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob) -> StageJobOutcome:
        relative_path = node_path(job.node_key)
        result_freeze_relative_path = node_path(IdentityBuilder.result_freeze_node_key(job.context))
        result_freeze = self._repository.read(result_freeze_relative_path)
        if not result_freeze.found or result_freeze.payload_bytes is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Result-freeze manifest is unavailable"
            )
        try:
            payload = render_frozen_report(result_freeze.payload_bytes)
        except ResultFreezeError as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, ((job.inputs[0], result_freeze_relative_path),)),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=commit.error_message or "report artifact commit failed",
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_artifact=job.output)


__all__ = ["ReportGenerationStageHandler"]
