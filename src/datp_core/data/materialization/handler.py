"""Dataset materialization stage handler — orchestration only."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.payloads import BytesPayload, FilePayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts.enums import ClientConstructionMethod
from datp_core.data.manifests.codec import encode_split_manifest, read_materialized_split_evidence
from datp_core.data.materialization.registry import DatasetAdapterRegistry
from datp_core.data.readiness.gates import evaluate_readiness_gates
from datp_core.data.readiness.source_audit import AuditDatasetUseCase
from datp_core.data.sources.inventory import build_source_inventory
from datp_core.experiments.planning import resolve_partition_contract
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import node_path
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class DatasetMaterializationStageHandler:
    stage = StageKind.DATASET_MATERIALIZATION

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        repository: ArtifactRepository,
        adapter_registry: DatasetAdapterRegistry,
    ) -> None:
        self._config = config
        self._repository = repository
        self._adapter_registry = adapter_registry

    def execute(self, job: StageJob) -> StageJobOutcome:
        experiment_id = job.context.experiment_id
        experiment = self._config.experiments.get(experiment_id)
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]

        setup = dataset.setup(population.setup_id)
        materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)

        relative_path = node_path(job.node_key)
        manifest_relative_path = f"{relative_path}.split_manifest"
        readiness_relative_path = f"{relative_path}.readiness"
        preprocessing_relative_path = f"{relative_path}.preprocessing"
        partition_relative_path = f"{relative_path}.partition_manifest"
        manifest_key = ArtifactKey(
            node_key=job.node_key,
            kind=ArtifactKind.SPLIT_MANIFEST,
        )
        readiness_key = ArtifactKey(
            node_key=job.node_key,
            kind=ArtifactKind.DATASET_READINESS,
        )
        preprocessing_key = ArtifactKey(
            node_key=job.node_key,
            kind=ArtifactKind.PREPROCESSING_EVIDENCE,
        )
        partition_key = (
            ArtifactKey(
                node_key=job.node_key,
                kind=ArtifactKind.PARTITION_MANIFEST,
            )
            if setup.client_construction.method == ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS
            else None
        )
        try:
            partition_condition, partition_seed_contract = resolve_partition_contract(
                self._config, experiment_id, job.context.partition_condition
            )
        except ValueError as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        if (partition_key is None) != (partition_condition is None):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Dataset setup and job partition condition are incompatible",
            )
        inventory = build_source_inventory(dataset)
        source_fingerprint = inventory.fingerprint()

        try:
            adapter = self._adapter_registry.get(dataset.adapter_kind)
        except KeyError as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )

        try:
            with TemporaryDirectory(prefix=f"datp_{dataset.dataset_id.value}_") as staging_directory:
                staging_root = Path(staging_directory)
                payload = adapter.materialize(
                    dataset=dataset,
                    setup=setup,
                    materialization=materialization,
                    inventory=inventory,
                    staging_root=staging_root,
                    partition_condition=partition_condition,
                    partition_seed_contract=partition_seed_contract,
                    chunk_row_count=self._config.runtime.active_execution_profile.data_loading.chunk_row_count.value,
                )
                # Close the TOCTOU window: verify the source files that were actually read during
                # materialization still match the inventory the path computation above was based on.
                # A source change mid-run must never commit under a stale artifact identity.
                post_materialization_fingerprint = build_source_inventory(dataset).fingerprint()
                if post_materialization_fingerprint != source_fingerprint:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message=(
                            "Source files changed during materialization: expected source-inventory "
                            f"fingerprint {source_fingerprint.value}, observed "
                            f"{post_materialization_fingerprint.value} after materialization completed. "
                            "This run's identity is no longer valid for these source files; a newly "
                            "planned run is required."
                        ),
                    )
                eligibility = self._config.eligibility_policies.get(dataset.eligibility_policy_id)
                split_evidence = read_materialized_split_evidence(
                    str(payload.staged_path), int(eligibility.minimum_benign_calibration_count)
                )
                readiness = AuditDatasetUseCase().assess_materialization(
                    dataset, setup, split_evidence, inventory.fingerprint()
                )
                if not readiness.ready_for_training:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message="Dataset readiness failed: "
                        + "; ".join(defect.code for defect in readiness.blocking_defects),
                    )
                gate_issues = evaluate_readiness_gates(
                    experiment.readiness_gates,
                    self._config.eligibility_gates,
                    split_evidence.manifest,
                    experiment.identifier,
                )
                if gate_issues:
                    return StageJobOutcome.infeasible(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message="Eligibility gate(s) failed: " + "; ".join(gate_issues),
                    )

                commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=job.output,
                    artifact_format=ArtifactFormat.PARQUET,
                    relative_path=relative_path,
                    parents=artifact_parents(
                        self._config,
                        tuple(
                            (input_key, node_path(dependency_key))
                            for input_key, dependency_key in zip(
                                job.inputs, job.dependencies, strict=True
                            )
                        ),
                        source_inventory_fingerprint=source_fingerprint,
                    ),
                    payload=FilePayload(source_file=str(payload.staged_path)),
                    source_inventory_fingerprint=source_fingerprint,
                )
                if not commit.success:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message=commit.error_message or "materialized artifact commit failed",
                    )

                manifest_commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=manifest_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=manifest_relative_path,
                    parents=artifact_parents(
                        self._config,
                        ((job.output, relative_path),),
                        source_inventory_fingerprint=source_fingerprint
                    ),
                    payload=BytesPayload(payload_bytes=encode_split_manifest(split_evidence.manifest)),
                    source_inventory_fingerprint=source_fingerprint,
                )
                if not manifest_commit.success:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message=manifest_commit.error_message or "split manifest commit failed",
                    )
                readiness_commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=readiness_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=readiness_relative_path,
                    parents=artifact_parents(
                        self._config,
                        ((job.output, relative_path),),
                        source_inventory_fingerprint=source_fingerprint
                    ),
                    payload=BytesPayload(payload_bytes=readiness.encode()),
                    source_inventory_fingerprint=source_fingerprint,
                )
                if not readiness_commit.success:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message=readiness_commit.error_message or "dataset readiness commit failed",
                    )
                preprocessing_commit = commit_artifact(
                    self._repository,
                    self._config,
                    job.context,
                    artifact_key=preprocessing_key,
                    artifact_format=ArtifactFormat.JSON,
                    relative_path=preprocessing_relative_path,
                    parents=artifact_parents(
                        self._config,
                        ((job.output, relative_path),),
                        source_inventory_fingerprint=source_fingerprint
                    ),
                    payload=BytesPayload(payload_bytes=payload.preprocessing_evidence),
                    source_inventory_fingerprint=source_fingerprint,
                )
                if not preprocessing_commit.success:
                    return StageJobOutcome.failed(
                        node_key=job.node_key,
                        stage=job.stage,
                        error_message=preprocessing_commit.error_message or "preprocessing evidence commit failed",
                    )
                if partition_key is not None:
                    if payload.partition_evidence is None:
                        return StageJobOutcome.failed(
                            node_key=job.node_key,
                            stage=job.stage,
                            error_message="Dirichlet materialization did not produce partition evidence",
                        )
                    partition_commit = commit_artifact(
                        self._repository,
                        self._config,
                        job.context,
                        artifact_key=partition_key,
                        artifact_format=ArtifactFormat.JSON,
                        relative_path=partition_relative_path,
                        parents=artifact_parents(
                            self._config,
                            ((job.output, relative_path),),
                            source_inventory_fingerprint=source_fingerprint
                        ),
                        payload=BytesPayload(payload_bytes=payload.partition_evidence),
                        source_inventory_fingerprint=source_fingerprint,
                    )
                    if not partition_commit.success:
                        return StageJobOutcome.failed(
                            node_key=job.node_key,
                            stage=job.stage,
                            error_message=partition_commit.error_message or "partition manifest commit failed",
                        )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_artifact=job.output)
