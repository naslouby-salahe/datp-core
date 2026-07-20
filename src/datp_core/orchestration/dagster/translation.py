"""Translation mechanics converting DATP execution plans into Dagster AssetSpecs and AssetKeys."""

from __future__ import annotations

from dagster import AssetKey, AssetSpec

from datp_core.domain.artifacts import ArtifactKey
from datp_core.domain.outcomes import StageJob
from datp_core.planning.graph import PlanningGraph


def artifact_key_to_dagster_asset_key(artifact_key: ArtifactKey) -> AssetKey:
    """Map canonical DATP ArtifactKey to Dagster AssetKey hierarchy."""
    clean_id = artifact_key.artifact_id.value.replace(":", "/")
    return AssetKey(["datp", artifact_key.kind.value, clean_id])


def stage_job_to_asset_spec(job: StageJob) -> AssetSpec:
    """Translate single DATP StageJob into Dagster AssetSpec."""
    asset_key = artifact_key_to_dagster_asset_key(job.output)
    deps = [artifact_key_to_dagster_asset_key(inp) for inp in job.inputs]
    return AssetSpec(
        key=asset_key,
        deps=deps,
        metadata={
            "job_id": job.job_id.value,
            "stage": job.stage.value,
        },
    )


def translate_planning_graph_to_asset_specs(graph: PlanningGraph) -> tuple[AssetSpec, ...]:
    """Translate complete DATP PlanningGraph into a sequence of Dagster AssetSpecs."""
    return tuple(stage_job_to_asset_spec(j) for j in graph.jobs)
