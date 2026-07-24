"""Score-generation pipeline stage: score one materialized split from its selected checkpoint."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame, validate_test_score_frame
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts.enums import SplitMembership, SplitMethod
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.identity.kinds import IdentityKind
from datp_core.learning.contracts.enums import (
    CheckpointAuthorization,
    DevicePolicy,
    PersonalizationStrategy,
    ScoreOrientation,
)
from datp_core.learning.model.device import require_cuda_training_device
from datp_core.learning.scoring.checkpoints import (
    build_model_from_checkpoint_bytes,
    build_personalized_models_from_bytes,
)
from datp_core.learning.scoring.compute import (
    score_materialized_split,
    score_personalized_materialized_split,
)
from datp_core.learning.scoring.data import materialized_feature_columns
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import node_path
from datp_core.pipeline.stages.outcomes import StageJobOutcome


def _score_split(kind: ArtifactKind, context: StageJobContext, config: ResolvedProjectConfiguration) -> str | None:
    """Resolve the named split for a score artifact kind."""
    experiment = config.experiments.get(context.experiment_id)
    population = config.populations.get(context.population_id or experiment.population_ids[0])
    dataset = config.datasets.get(population.dataset_id)
    setup = dataset.setup(population.setup_id)
    materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
    temporal = materialization.split_method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL
    if kind is ArtifactKind.CALIBRATION_SCORES:
        return SplitMembership.HISTORICAL_CALIBRATION.value if temporal else SplitMembership.CALIBRATION.value
    if kind is ArtifactKind.FUTURE_RECALIBRATION_SCORES:
        return SplitMembership.FUTURE_RECALIBRATION.value if temporal else None
    if kind is ArtifactKind.TEST_SCORES:
        return SplitMembership.FUTURE_EVALUATION.value if temporal else SplitMembership.TEST.value
    return None


class ScoreGenerationStageHandler:
    """Score one authorized materialized split from its selected model checkpoint."""

    stage = StageKind.SCORE_GENERATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob) -> StageJobOutcome:
        split = _score_split(job.output.kind, job.context, self._config)
        if split is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Unknown score artifact kind"
            )
        relative_path = node_path(job.node_key)
        experiment = self._config.experiments.get(job.context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        training_path = node_path(IdentityBuilder.training_node_key(job.context))
        selection_path, selection_key = self._selection_location(job, profile.checkpoint_authorization)
        selection = self._repository.read(selection_path)
        if not selection.found or selection.payload_bytes is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Selected-checkpoint evidence is unreadable"
            )
        checkpoint = self._repository.read(training_path)
        personalized_key = IdentityBuilder.artifact_key(IdentityKind.PERSONALIZED_CHECKPOINT, job.context)
        personalized_path = f"{training_path}.personalized"
        personalized = (
            self._repository.read(personalized_path)
            if profile.personalization == PersonalizationStrategy.DITTO
            else None
        )
        materialization_path = node_path(IdentityBuilder.materialization_node_key(job.context))
        materialization = self._repository.read(materialization_path)
        if not checkpoint.found or checkpoint.payload_bytes is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Model checkpoint is unavailable"
            )
        if not materialization.found or materialization.payload_bytes is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Materialization artifact is unavailable"
            )
        if profile.personalization == PersonalizationStrategy.DITTO and (
            personalized is None or not personalized.found or personalized.payload_bytes is None
        ):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Personalized checkpoint is unavailable or incompatible",
            )
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        features = dataset.field_schema.model_features
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            if self._config.runtime.active_execution_profile.device_policy != DevicePolicy.CUDA_REQUIRED.value:
                raise ValueError("Score generation requires the configured CUDA-required execution profile")
            with TemporaryDirectory(prefix="datp_scoring_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization.payload_bytes)
                feature_columns = (
                    features.order if features is not None else materialized_feature_columns(materialized_path)
                )
                selected_round = json.loads(selection.payload_bytes)["selected_round"]
                if profile.personalization == PersonalizationStrategy.DITTO:
                    if personalized is None or personalized.payload_bytes is None:
                        raise ValueError("Personalized checkpoint is unavailable for Ditto scoring")
                    client_ids = (
                        pl.read_parquet(materialized_path, columns=["client_id"])["client_id"].unique().sort().to_list()
                    )
                    models = build_personalized_models_from_bytes(
                        personalized.payload_bytes,
                        selected_round,
                        client_ids,
                        len(feature_columns),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_personalized_materialized_split(
                        models,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                else:
                    model = build_model_from_checkpoint_bytes(
                        checkpoint.payload_bytes,
                        selected_round,
                        len(feature_columns),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_materialized_split(
                        model,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                scores = scores.with_columns(
                    pl.lit(
                        personalized_key.node_key.label
                        if profile.personalization == PersonalizationStrategy.DITTO
                        else job.inputs[0].node_key.label
                    ).alias("checkpoint_artifact_id"),
                    pl.lit(job.context.seed).alias("seed"),
                    pl.lit(ScoreOrientation.HIGHER_MORE_ANOMALOUS.value).alias("score_orientation"),
                )
        except (OSError, RuntimeError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        validated = (
            validate_calibration_score_frame(scores)
            if job.output.kind
            in {
                ArtifactKind.CALIBRATION_SCORES,
                ArtifactKind.FUTURE_RECALIBRATION_SCORES,
            }
            else validate_test_score_frame(scores)
        )
        payload = BytesIO()
        validated.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(
                self._config,
                (
                    (job.inputs[0], training_path),
                    (job.inputs[1], materialization_path),
                    (selection_key, selection_path),
                    *(
                        ((personalized_key, personalized_path),)
                        if profile.personalization == PersonalizationStrategy.DITTO
                        else ()
                    ),
                ),
            ),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message=commit.error_message or "score artifact commit failed"
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_artifact=job.output)

    def _selection_location(
        self, job: StageJob, authorization: CheckpointAuthorization
    ) -> tuple[str, ArtifactKey]:
        if authorization == CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE:
            selection_context = StageJobContext(experiment_id=job.context.experiment_id)
            return (
                node_path(IdentityBuilder.cohort_checkpoint_selection_node_key(selection_context)),
                IdentityBuilder.artifact_key(IdentityKind.COHORT_CHECKPOINT_SELECTION, selection_context),
            )
        if authorization == CheckpointAuthorization.LOOKUP_OF_FEDERATED_AVERAGING:
            source = self._config.primary_federated_checkpoint_experiment()
            selection_context = StageJobContext(experiment_id=source.identifier)
            return (
                node_path(IdentityBuilder.cohort_checkpoint_selection_node_key(selection_context)),
                IdentityBuilder.artifact_key(IdentityKind.COHORT_CHECKPOINT_SELECTION, selection_context),
            )
        selection_key = ArtifactKey(
            node_key=job.inputs[0].node_key,
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )
        return (
            f"{node_path(IdentityBuilder.training_node_key(job.context))}.selection",
            selection_key,
        )
