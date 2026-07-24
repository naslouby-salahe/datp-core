"""Closed artifact identity concepts: kind, format, lifecycle state, and the artifact key."""

from __future__ import annotations

from enum import Enum

from attrs import define

from datp_core.pipeline.stages.node_key import StageNodeKey


class ArtifactKind(Enum):
    RESOLVED_CONFIG = "resolved_config"
    MATERIALIZED_DATASET = "materialized_dataset"
    SPLIT_MANIFEST = "split_manifest"
    PARTITION_MANIFEST = "partition_manifest"
    DATASET_READINESS = "dataset_readiness"
    PREPROCESSING_EVIDENCE = "preprocessing_evidence"
    MODEL_CHECKPOINT = "model_checkpoint"
    PERSONALIZED_MODEL_CHECKPOINT = "personalized_model_checkpoint"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    CALIBRATION_SCORES = "calibration_scores"
    FUTURE_RECALIBRATION_SCORES = "future_recalibration_scores"
    CALIBRATION_SUBSET = "calibration_subset"
    TEST_SCORES = "test_scores"
    THRESHOLDS = "thresholds"
    THRESHOLD_DIAGNOSTICS = "threshold_diagnostics"
    CLIENT_METRICS = "client_metrics"
    STATISTICAL_SUMMARY = "statistical_summary"
    RESULT_FREEZE = "result_freeze"
    RESULT_REPORT = "result_report"
    REPORT = "report"


class ArtifactFormat(Enum):
    JSON = "json"
    PARQUET = "parquet"
    SAFETENSORS = "safetensors"
    TEXT = "text"


class ArtifactState(Enum):
    """The atomic commit transaction is all-or-nothing: no partial/pending state is ever
    reader-visible, so FROZEN is the only lifecycle state a committed manifest can carry."""

    FROZEN = "frozen"


class ArtifactCorruptionReason(Enum):
    CHECKSUM_MISMATCH = "checksum_mismatch"
    MANIFEST_MISSING = "manifest_missing"
    PAYLOAD_MISSING = "payload_missing"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"


@define(frozen=True, slots=True, kw_only=True)
class ArtifactKey:
    node_key: StageNodeKey
    kind: ArtifactKind

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.node_key.label}"
