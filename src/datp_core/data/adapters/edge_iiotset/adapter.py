"""Edge-IIoTset adapter orchestration."""

from __future__ import annotations

import msgspec

from datp_core.data.adapters.edge_iiotset.materializer import EdgeVocabularyEvidence, materialize_edge_iiotset
from datp_core.data.contracts.enums import AdapterKind, DataFailureCode
from datp_core.data.materialization.database import open_database, require_non_empty_parquet
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import (
    EdgeIIoTsetMaterializationPlan,
    MaterializationRequest,
    StandardMaterializationResult,
)
from datp_core.data.materialization.normalization import NormalizationEvidence, normalize_materialized_parquet


class EdgePreprocessingEvidence(msgspec.Struct, frozen=True):
    vocabulary: EdgeVocabularyEvidence
    normalization: NormalizationEvidence


class EdgeIIoTsetAdapter:
    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.EDGE_IIOTSET

    def materialize(self, request: MaterializationRequest) -> StandardMaterializationResult:
        if not isinstance(request.plan, EdgeIIoTsetMaterializationPlan):
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "Edge-IIoTset adapter received an incompatible materialization plan",
                source_path=None,
                source_row_index=None,
            )
        plan = request.plan
        connection = open_database(request.layout.database, request.layout.temporary_directory, plan.runtime)
        try:
            output = materialize_edge_iiotset(
                connection,
                plan,
                request.inventory,
                request.layout.encoded_payload,
            )
            normalization = normalize_materialized_parquet(
                connection,
                request.layout.encoded_payload,
                request.layout.final_payload,
                output.numeric_feature_names,
                plan.normalization,
                plan.runtime,
            )
        finally:
            connection.close()
        require_non_empty_parquet(request.layout.final_payload)
        preprocessing = EdgePreprocessingEvidence(
            vocabulary=output.vocabulary,
            normalization=normalization,
        )
        return StandardMaterializationResult(
            staged_path=request.layout.final_payload,
            row_count=output.evidence.written_rows,
            preprocessing_evidence=msgspec.json.encode(preprocessing),
            materialization_evidence=output.evidence,
        )
