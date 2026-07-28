"""N-BaIoT adapter orchestration."""

from __future__ import annotations

from datp_core.data.adapters.nbaiot.materializer import materialize_nbaiot
from datp_core.data.adapters.nbaiot.partitioning import encode_partition_evidence
from datp_core.data.contracts.enums import AdapterKind, DataFailureCode
from datp_core.data.materialization.database import open_database, require_non_empty_parquet
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import (
    MaterializationRequest,
    NBaIoTDirichletMaterializationPlan,
    NBaIoTPhysicalMaterializationPlan,
    PartitionedMaterializationResult,
    StandardMaterializationResult,
)
from datp_core.data.materialization.normalization import encode_normalization_evidence, normalize_materialized_parquet


class NBaIoTAdapter:
    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.NBAIOT

    def materialize(
        self, request: MaterializationRequest
    ) -> StandardMaterializationResult | PartitionedMaterializationResult:
        if not isinstance(request.plan, NBaIoTPhysicalMaterializationPlan | NBaIoTDirichletMaterializationPlan):
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "N-BaIoT adapter received an incompatible materialization plan",
                source_path=None,
                source_row_index=None,
            )
        plan = request.plan
        connection = open_database(request.layout.database, request.layout.temporary_directory, plan.runtime)
        try:
            evidence, partition = materialize_nbaiot(
                connection,
                plan,
                request.inventory,
                request.layout.raw_payload,
            )
            normalization = normalize_materialized_parquet(
                connection,
                request.layout.raw_payload,
                request.layout.final_payload,
                evidence.encoded_feature_names,
                plan.normalization,
                plan.runtime,
            )
        finally:
            connection.close()
        require_non_empty_parquet(request.layout.final_payload)
        if partition is None:
            return StandardMaterializationResult(
                staged_path=request.layout.final_payload,
                row_count=evidence.written_rows,
                preprocessing_evidence=encode_normalization_evidence(normalization),
                materialization_evidence=evidence,
            )
        return PartitionedMaterializationResult(
            staged_path=request.layout.final_payload,
            row_count=evidence.written_rows,
            preprocessing_evidence=encode_normalization_evidence(normalization),
            partition_evidence=encode_partition_evidence(partition),
            materialization_evidence=evidence,
        )
