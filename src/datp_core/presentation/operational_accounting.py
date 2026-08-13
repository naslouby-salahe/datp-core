from collections import defaultdict
from pathlib import Path

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.operational.communication import (
    ThresholdPayloadKind,
)
from datp_core.core.identifiers import FederatedThresholdMethod, FileContentText
from datp_core.runtime.filesystem import write_text_atomically


def export_threshold_stage_accounting(documents: tuple[FederatedEvaluationDocument, ...], destination: Path) -> Path:
    """Publish persisted threshold-only transport and coordinator disclosure evidence."""
    by_method: dict[FederatedThresholdMethod, list[FederatedEvaluationDocument]] = defaultdict(list)
    for document in documents:
        by_method[document.threshold_method].append(document)
    lines = [
        "# Threshold-stage communication, storage, and runtime accounting",
        "",
        "All rows describe threshold construction after score arrays are materialized; detector scoring and disk I/O "
        "are excluded. Serialized byte counts are taken from persisted serializer-bound diagnostics.",
        "",
        "| Policy | Seeds | Logical fields | Serialized bytes by seed | Coordinator observes "
        "threshold / moments / fingerprint / sketch / family / cluster assignment | Raw calibration records |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for method, method_documents in sorted(by_method.items(), key=lambda item: item[0].value):
        ordered = tuple(sorted(method_documents, key=lambda item: item.score_coordinate.training_seed))
        diagnostics = tuple(item.diagnostics.threshold_stage_communication for item in ordered)
        if any(item is None for item in diagnostics):
            lines.append(f"| `{method.value}` | {len(ordered)} | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | no |")
            continue
        available = tuple(item for item in diagnostics if item is not None)
        kinds = frozenset(message.payload_kind for diagnostic in available for message in diagnostic.messages)
        logical = ", ".join(
            f"{diagnostic.training_seed.value}:{diagnostic.total_logical_element_count.value}"
            for diagnostic in available
        )
        bytes_by_seed = ", ".join(
            f"{diagnostic.training_seed.value}:{diagnostic.total_serialized_bytes.value}" for diagnostic in available
        )
        lines.append(
            f"| `{method.value}` | {len(ordered)} | {logical or '0'} | {bytes_by_seed or '0'} | "
            f"{_disclosures(kinds)} | no |"
        )
    lines.extend(
        (
            "",
            "Family identity already present in an authenticated population manifest is not counted as per-execution "
            "communication. This report makes no privacy-preserving claim.",
        )
    )
    return write_text_atomically(destination, FileContentText("\n".join(lines) + "\n"))


def _disclosures(kinds: frozenset[ThresholdPayloadKind]) -> str:
    threshold = ThresholdPayloadKind.LOCAL_QUANTILE_TRANSMISSION in kinds
    moments = ThresholdPayloadKind.BENIGN_SUMMARY_STATISTICS in kinds
    fingerprint = ThresholdPayloadKind.CLUSTER_FINGERPRINT_TRANSMISSION in kinds
    sketch = ThresholdPayloadKind.KLL_SKETCH_TRANSMISSION in kinds
    cluster_assignment = ThresholdPayloadKind.GROUPED_THRESHOLD_ASSIGNMENT in kinds
    return "; ".join(
        (
            f"threshold={'yes' if threshold else 'no'}",
            f"moments={'yes' if moments else 'no'}",
            f"fingerprint={'yes' if fingerprint else 'no'}",
            f"sketch={'yes' if sketch else 'no'}",
            "family=pre-existing metadata",
            f"cluster_assignment={'yes' if cluster_assignment else 'no'}",
        )
    )
