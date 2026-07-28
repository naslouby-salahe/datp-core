"""CICIoT2023 adapter orchestration."""

from __future__ import annotations

from datp_core.data.adapters.ciciot2023.materializer import materialize_ciciot2023
from datp_core.data.contracts.enums import AdapterKind, DataFailureCode
from datp_core.data.materialization.database import open_database, require_non_empty_parquet
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import (
    CICIoT2023MaterializationPlan,
    MaterializationRequest,
    StandardMaterializationResult,
)
from datp_core.data.materialization.normalization import encode_normalization_evidence, normalize_materialized_parquet


class CICIoT2023Adapter:
    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.CICIOT2023

    def materialize(self, request: MaterializationRequest) -> StandardMaterializationResult:
        if not isinstance(request.plan, CICIoT2023MaterializationPlan):
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "CICIoT2023 adapter received an incompatible materialization plan",
                source_path=None,
                source_row_index=None,
            )
        plan = request.plan
        connection = open_database(request.layout.database, request.layout.temporary_directory, plan.runtime)
        try:
            evidence = materialize_ciciot2023(connection, plan, request.inventory, request.layout.raw_payload)
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
        return StandardMaterializationResult(
            staged_path=request.layout.final_payload,
            row_count=evidence.written_rows,
            preprocessing_evidence=encode_normalization_evidence(normalization),
            materialization_evidence=evidence,
        )
