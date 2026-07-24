"""Deterministic, nested benign-calibration subsampling for boundary experiments, and the
calibration-subsampling pipeline stage.

`_subsample_seed` delegates to the single canonical deterministic-seed-derivation formula in
`pipeline/determinism.py` (consolidating what were three independent but byte-identical
reimplementations across the pre-refactor codebase -- see that module's docstring).
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
import polars as pl

from datp_core.artifacts.models import ArtifactFormat, ArtifactRepository, BytesPayload
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.contracts.frames import validate_calibration_score_frame
from datp_core.core.hashing import derive_seed
from datp_core.core.identifiers import RunId
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import score_context
from datp_core.pipeline.execution import artifact_parents, commit_artifact
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind


def subsample_calibration_scores(
    scores: pl.DataFrame,
    *,
    requested_sample_count: int,
    training_seed: int,
    selection_seed: int,
    replicate: int,
    namespace_key: str,
    digest_bytes: int,
) -> pl.DataFrame:
    """Return each eligible client's deterministic prefix of its replicate permutation.

    The permutation is independent of requested size, making smaller windows exact prefixes
    of larger windows for the same seed, client, and replicate.
    """
    if requested_sample_count < 1 or replicate < 0 or digest_bytes < 1 or not namespace_key:
        raise ValueError(
            "Calibration subsampling requires positive size, namespace digest, and a non-negative replicate"
        )
    required = {"client_id", "source_path", "source_row_index", "score"}
    if missing := required - set(scores.columns):
        raise ValueError(f"Calibration scores lack deterministic subsampling columns: {', '.join(sorted(missing))}")
    ordered = scores.sort("client_id", "source_path", "source_row_index")
    samples: list[pl.DataFrame] = []
    for client, client_scores in ordered.group_by("client_id", maintain_order=True):
        if client_scores.height < requested_sample_count:
            continue
        seed = _subsample_seed(
            namespace_key,
            digest_bytes,
            client_id=str(client[0]),
            training_seed=training_seed,
            selection_seed=selection_seed,
            replicate=replicate,
        )
        positions = np.random.default_rng(seed).permutation(client_scores.height)[:requested_sample_count]
        samples.append(client_scores.gather(pl.Series(positions)).sort("source_path", "source_row_index"))
    if not samples:
        return ordered.head(0)
    return pl.concat(samples).sort("client_id", "source_path", "source_row_index")


def _subsample_seed(
    key: str,
    digest_bytes: int,
    *,
    client_id: str,
    training_seed: int,
    selection_seed: int,
    replicate: int,
) -> int:
    return derive_seed(
        key,
        digest_bytes,
        (
            ("client_identifier", client_id),
            ("replicate_index", replicate),
            ("selection_seed", selection_seed),
            ("training_seed", training_seed),
        ),
    )


class CalibrationSubsamplingStageHandler:
    """Persist one nested, benign-only calibration window without retraining or rescoring."""

    stage = StageKind.CALIBRATION_SUBSAMPLING

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        context = job.context
        if context.seed is None or context.calibration_sample_count is None or context.calibration_replicate is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subsampling requires a seed, sample count, and replicate",
            )
        experiment = self._config.experiments.get(context.experiment_id)
        subset = experiment.calibration_subset
        if subset is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subsampling is not configured for this experiment",
            )
        if (
            subset.selection_strategy != "deterministic_without_replacement"
            or subset.nesting_policy != "nested_by_size"
            or subset.model_retraining != "never_thresholds_only_recomputed"
            or subset.replicate_seed_derivation != "derived_seed_algorithm_with_namespace_calibration_subsample"
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subset contract is not executable by the configured deterministic sampler",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        calibration = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(score_context(context)).value}"
        )
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        try:
            namespace = self._config.protocol_determinism.seed_namespaces["calibration_subsample"]
            digest_bytes = int(self._config.protocol_determinism.derived_seed_algorithm["digest_bytes"])
            scores = validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes)))
            sampled = subsample_calibration_scores(
                scores,
                requested_sample_count=context.calibration_sample_count,
                training_seed=context.seed,
                selection_seed=subset.selection_seed.value,
                replicate=context.calibration_replicate,
                namespace_key=namespace.key,
                digest_bytes=digest_bytes,
            )
            validate_calibration_score_frame(sampled)
        except (KeyError, OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        sampled.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "calibration subset commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
