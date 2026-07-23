"""Pipeline stages for result freezing and report generation."""

from __future__ import annotations

from datp_core.artifacts.models import ArtifactFormat, ArtifactRepository, BytesPayload
from datp_core.artifacts.provenance import git_revision
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.experiments.identity import IdentityBuilder
from datp_core.pipeline.identifiers import RunId
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact
from datp_core.reporting.freezing import ResultFreezeError, freeze_result_family
from datp_core.reporting.rendering import render_frozen_report


class ResultFreezeStageHandler:
    """Close and validate immutable provenance before report rendering."""

    stage = StageKind.RESULT_FREEZE

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        statistics = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.statistical_analysis_job_id(job.context).value}"
        )
        if not statistics.found or statistics.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Statistical summary is unavailable"
            )
        experiment = self._config.experiments.get(job.context.experiment_id)
        try:
            profiles = tuple(self._config.report_profiles.get(identifier) for identifier in experiment.report_ids)
            seed_cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
            primary_population = experiment.population_ids[0] if experiment.population_ids else None
            population_record = (
                self._config.populations.get(primary_population) if primary_population is not None else None
            )
            source_revision = git_revision()
            payload = freeze_result_family(
                experiment=experiment,
                report_profiles=profiles,
                statistical_summary=statistics.payload_bytes,
                source_artifacts=job.inputs,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_revision=source_revision,
                seed_count=len(seed_cohort.training_seeds),
                dataset_id=population_record.dataset_id.value if population_record is not None else None,
            )
        except (KeyError, ResultFreezeError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "result-freeze artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class ReportGenerationStageHandler:
    """Render configured report artifacts exclusively from a frozen result manifest."""

    stage = StageKind.REPORT_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        result_freeze = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.result_freeze_job_id(job.context).value}"
        )
        if not result_freeze.found or result_freeze.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Result-freeze manifest is unavailable"
            )
        try:
            payload = render_frozen_report(result_freeze.payload_bytes)
        except ResultFreezeError as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "report artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


__all__ = ["ReportGenerationStageHandler", "ResultFreezeStageHandler"]
