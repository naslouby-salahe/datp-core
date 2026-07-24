"""Preflight stage handler — moved from data/materialization."""

from __future__ import annotations

import json

from datp_core.artifacts.identity import ArtifactFormat
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import RunId
from datp_core.pipeline.execution import commit_artifact
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind


class PreflightStageHandler:
    stage = StageKind.PREFLIGHT

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        payload = json.dumps(
            {
                "run_id": run_id.value,
                "schema_version": 1,
                "scientific_fingerprint": self._config.scientific_fingerprint.value,
                "execution_fingerprint": self._config.execution_fingerprint.value,
                "scientific_projection": self._config.scientific_projection,
                "execution_projection": self._config.execution_projection,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        reuse = self._repository.assess_reuse(
            relative_path,
            job.output,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        )
        if reuse.can_reuse:
            return StageJobOutcome.reused(
                job_id=job.job_id,
                stage=job.stage,
                produced_artifact=job.output,
            )
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=(),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "artifact commit failed",
            )
        return StageJobOutcome.succeeded(
            job_id=job.job_id,
            stage=job.stage,
            produced_artifact=job.output,
        )
