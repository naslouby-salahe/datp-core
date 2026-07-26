"""Dataset materialization stage handler."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts.enums import ClientConstructionMethod
from datp_core.data.manifests.codec import encode_split_manifest, read_materialized_split_evidence
from datp_core.data.materialization.registry import DatasetAdapterRegistry
from datp_core.data.readiness.gates import evaluate_readiness_gates
from datp_core.data.readiness.source_audit import AuditDatasetUseCase
from datp_core.data.sources.inventory import build_source_inventory
from datp_core.experiments.planning import resolve_partition_contract
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class DatasetMaterializationStageHandler:
    stage = StageKind.DATASET_MATERIALIZATION

    def __init__(
        self, config: ResolvedProjectConfiguration, store: ArtifactStore, adapter_registry: DatasetAdapterRegistry
    ) -> None:
        self._config = config
        self._store = store
        self._adapter_registry = adapter_registry

    def execute(self, job: StageJob) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        population = self._config.populations.get(job.context.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        setup = dataset.setup(population.setup_id)
        materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
        try:
            partition_condition, partition_seed_contract = resolve_partition_contract(
                self._config, experiment.identifier, job.context.partition_condition
            )
            has_partition_output = any(item.name == "partition_manifest" for item in job.outputs)
            expects_partition = (
                setup.client_construction.method is ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS
            )
            if has_partition_output != expects_partition or (partition_condition is None) != (not expects_partition):
                raise ValueError("Dataset setup and job partition condition are incompatible")
            adapter = self._adapter_registry.get(dataset.adapter_kind)
        except (KeyError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        inventory = build_source_inventory(dataset)
        source_fingerprint = inventory.fingerprint()
        try:
            with TemporaryDirectory(prefix=f"datp_{dataset.dataset_id.value}_") as staging_directory:
                payload = adapter.materialize(
                    dataset=dataset,
                    setup=setup,
                    materialization=materialization,
                    inventory=inventory,
                    staging_root=Path(staging_directory),
                    partition_condition=partition_condition,
                    partition_seed_contract=partition_seed_contract,
                    chunk_row_count=self._config.runtime.active_execution_profile.data_loading.chunk_row_count.value,
                )
                observed_fingerprint = build_source_inventory(dataset).fingerprint()
                if observed_fingerprint != source_fingerprint:
                    raise ValueError(
                        "Source files changed during materialization: expected source-inventory "
                        f"fingerprint {source_fingerprint.value}, observed {observed_fingerprint.value}"
                    )
                eligibility = self._config.eligibility_policies.get(dataset.eligibility_policy_id)
                split_evidence = read_materialized_split_evidence(
                    str(payload.staged_path), int(eligibility.minimum_benign_calibration_count)
                )
                readiness = AuditDatasetUseCase().assess_materialization(
                    dataset, setup, split_evidence, source_fingerprint
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
                self._store.write_file_atomic(job.output_path("dataset"), payload.staged_path)
                self._store.write_bytes_atomic(
                    job.output_path("split_manifest"), encode_split_manifest(split_evidence.manifest)
                )
                self._store.write_bytes_atomic(job.output_path("readiness"), readiness.encode())
                self._store.write_bytes_atomic(job.output_path("preprocessing"), payload.preprocessing_evidence)
                if expects_partition:
                    if payload.partition_evidence is None:
                        raise ValueError("Dirichlet materialization did not produce partition evidence")
                    self._store.write_bytes_atomic(job.output_path("partition_manifest"), payload.partition_evidence)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
