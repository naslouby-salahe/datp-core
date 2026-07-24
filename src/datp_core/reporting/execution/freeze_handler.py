"""Pipeline stage for result freezing."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactFormat
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.provenance import git_revision
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
from datp_core.reporting.freezing.service import freeze_result_family


class ResultFreezeStageHandler:
    """Close and validate immutable provenance before report rendering."""

    stage = StageKind.RESULT_FREEZE

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob) -> StageJobOutcome:
        relative_path = node_path(job.node_key)
        statistics = self._repository.read(
            node_path(IdentityBuilder.statistical_analysis_node_key(job.context))
        )
        if not statistics.found or statistics.payload_bytes is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Statistical summary is unavailable"
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
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(
                self._config,
                tuple(
                    (input_key, node_path(dependency))
                    for input_key, dependency in zip(job.inputs, job.dependencies, strict=True)
                ),
            ),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=commit.error_message or "result-freeze artifact commit failed",
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_artifact=job.output)


__all__ = ["ResultFreezeStageHandler"]
