"""Preflight stage handler — moved from data/materialization."""

from __future__ import annotations

import json

from datp_core.artifacts.identity import ArtifactFormat
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import node_path
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class PreflightStageHandler:
    stage = StageKind.PREFLIGHT

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob) -> StageJobOutcome:
        payload = json.dumps(
            {
                "experiment_id": job.context.experiment_id.value,
                "schema_version": 1,
                "scientific_fingerprint": self._config.scientific_fingerprint.value,
                "execution_fingerprint": self._config.execution_fingerprint.value,
                "scientific_projection": self._config.scientific_projection,
                "execution_projection": self._config.execution_projection,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        relative_path = node_path(job.node_key)
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
                node_key=job.node_key,
                stage=job.stage,
                error_message=commit.error_message or "artifact commit failed",
            )
        return StageJobOutcome.succeeded(
            node_key=job.node_key,
            stage=job.stage,
            produced_artifact=job.output,
        )
