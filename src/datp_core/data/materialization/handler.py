"""Dataset-materialization stage coordination."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from datp_core.artifacts.store import ArtifactStore
from datp_core.data.contracts.enums import DataFailureCode, MaterializationArtifactKind
from datp_core.data.manifests.summary import (
    build_materialized_split_summary,
    encode_materialized_split_summary,
)
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import (
    MaterializationArtifactLayout,
    MaterializationPlanResolver,
    MaterializationRequest,
    PartitionedMaterializationResult,
)
from datp_core.data.materialization.registry import DatasetAdapterRegistry
from datp_core.data.materialization.schema import MaterializedSchemaSpec, validate_materialized_parquet
from datp_core.data.readiness.gates import evaluate_readiness_gates
from datp_core.data.readiness.materialized import assess_materialized_readiness
from datp_core.data.readiness.models import (
    DatasetAuditIssue,
    build_readiness_report,
    encode_readiness_report,
)
from datp_core.data.readiness.source import assess_source_readiness
from datp_core.data.sources.inventory import build_source_inventory
from datp_core.pipeline.stages.context import DataContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class DatasetMaterializationStageHandler:
    stage = StageKind.DATASET_MATERIALIZATION

    def __init__(
        self,
        store: ArtifactStore,
        plan_resolver: MaterializationPlanResolver,
        adapter_registry: DatasetAdapterRegistry,
    ) -> None:
        self._store = store
        self._plan_resolver = plan_resolver
        self._adapter_registry = adapter_registry

    def execute(self, job: StageJob) -> StageJobOutcome:
        if not isinstance(job.context, DataContext):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="dataset materialization requires DataContext",
            )
        try:
            plan = self._plan_resolver.resolve(job.context)
            inventory = build_source_inventory(plan.identity.dataset_id, plan.raw_data_root, plan.source)
            source_report = assess_source_readiness(plan.source, inventory)
            if source_report.blocking_issues:
                return StageJobOutcome.failed(
                    node_key=job.node_key,
                    stage=job.stage,
                    error_message=_issue_message("source readiness failed", source_report.blocking_issues),
                )
            plan.staging_parent.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(
                prefix=f"datp-{plan.identity.dataset_id.value}-",
                dir=plan.staging_parent,
            ) as staging_directory:
                staging_root = Path(staging_directory)
                layout = MaterializationArtifactLayout.for_staging_root(staging_root)
                result = self._adapter_registry.get(plan.adapter).materialize(
                    MaterializationRequest(
                        plan=plan,
                        inventory=inventory,
                        staging_root=staging_root,
                        layout=layout,
                    )
                )
                observed_inventory = build_source_inventory(
                    plan.identity.dataset_id,
                    plan.raw_data_root,
                    plan.source,
                )
                if observed_inventory.checksum != inventory.checksum:
                    raise DataFailure(
                        DataFailureCode.SOURCE_CHANGED,
                        "source inventory changed during materialization",
                        source_path=None,
                        source_row_index=None,
                    )
                schema_spec = MaterializedSchemaSpec(
                    shape=plan.artifact_shape,
                    feature_names=result.materialization_evidence.encoded_feature_names,
                )
                schema_validation = validate_materialized_parquet(
                    result.staged_path,
                    schema_spec,
                    int(plan.runtime.chunk_row_count),
                )
                summary = build_materialized_split_summary(
                    result.staged_path,
                    plan,
                    inventory.checksum,
                    schema_spec,
                    schema_validation,
                    result.materialization_evidence,
                    result.preprocessing_evidence,
                )
                materialized_report = assess_materialized_readiness(plan, summary)
                readiness = build_readiness_report(source_report, materialized_report)
                if not readiness.ready_for_training:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message=_issue_message("dataset readiness failed", readiness.blocking_issues),
                    )
                gate_failures = evaluate_readiness_gates(plan.readiness_gates, plan.capabilities, summary)
                if gate_failures:
                    return StageJobOutcome.infeasible(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message="readiness gates failed: "
                        + "; ".join(
                            f"{failure.gate_id}/{failure.code.value}: {failure.detail}"
                            for failure in gate_failures
                        ),
                    )
                _validate_output_contract(job, isinstance(result, PartitionedMaterializationResult))
                self._store.write_file_atomic(
                    job.output_path(MaterializationArtifactKind.DATASET.value),
                    result.staged_path,
                )
                self._store.write_bytes_atomic(
                    job.output_path(MaterializationArtifactKind.SPLIT_MANIFEST.value),
                    encode_materialized_split_summary(summary),
                )
                self._store.write_bytes_atomic(
                    job.output_path(MaterializationArtifactKind.READINESS.value),
                    encode_readiness_report(readiness),
                )
                self._store.write_bytes_atomic(
                    job.output_path(MaterializationArtifactKind.PREPROCESSING.value),
                    result.preprocessing_evidence,
                )
                if isinstance(result, PartitionedMaterializationResult):
                    self._store.write_bytes_atomic(
                        job.output_path(MaterializationArtifactKind.PARTITION_MANIFEST.value),
                        result.partition_evidence,
                    )
        except (DataFailure, OSError) as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )
        return StageJobOutcome.succeeded(
            node_key=job.node_key,
            stage=job.stage,
            produced_outputs=job.outputs,
        )


def _validate_output_contract(job: StageJob, partitioned: bool) -> None:
    expected = (
        MaterializationArtifactKind.DATASET.value,
        MaterializationArtifactKind.PREPROCESSING.value,
        MaterializationArtifactKind.READINESS.value,
        MaterializationArtifactKind.SPLIT_MANIFEST.value,
    ) + ((MaterializationArtifactKind.PARTITION_MANIFEST.value,) if partitioned else ())
    observed = tuple(sorted(output.name for output in job.outputs))
    if observed != tuple(sorted(expected)):
        raise DataFailure(
            DataFailureCode.ARTIFACT,
            "stage output contract mismatch; expected "
            + ", ".join(sorted(expected))
            + "; observed "
            + ", ".join(observed),
            source_path=None,
            source_row_index=None,
        )


def _issue_message(prefix: str, issues: tuple[DatasetAuditIssue, ...]) -> str:
    return prefix + ": " + "; ".join(f"{issue.code.value}: {issue.detail}" for issue in issues)
