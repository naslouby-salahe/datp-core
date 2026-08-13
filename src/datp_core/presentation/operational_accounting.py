from collections import defaultdict
from pathlib import Path

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    ThresholdPayloadKind,
    ThresholdStageCommunicationDiagnostic,
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
        "| Policy | Seeds | Logical fields | Raw-field bytes by seed | Serialized bytes by seed | Coordinator observes "
        "threshold / moments / fingerprint / sketch / family / cluster assignment | Raw calibration records |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for method, method_documents in sorted(by_method.items(), key=lambda item: item[0].value):
        ordered = tuple(sorted(method_documents, key=lambda item: item.score_coordinate.training_seed))
        diagnostics = tuple(item.diagnostics.threshold_stage_communication for item in ordered)
        if any(item is None for item in diagnostics):
            lines.append(
                f"| `{method.value}` | {len(ordered)} | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | no |"
            )
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
        raw_bytes_by_seed = _raw_bytes_by_seed(available)
        lines.append(
            f"| `{method.value}` | {len(ordered)} | {logical or '0'} | {raw_bytes_by_seed} | {bytes_by_seed or '0'} | "
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


def _raw_bytes_by_seed(diagnostics: tuple[ThresholdStageCommunicationDiagnostic, ...]) -> str:
    rendered: list[str] = []
    for diagnostic in diagnostics:
        raw_bytes = tuple(_raw_message_bytes(message) for message in diagnostic.messages)
        if any(value is None for value in raw_bytes):
            rendered.append(f"{diagnostic.training_seed.value}:no fixed bound (KLL sketch)")
        else:
            total = sum(value for value in raw_bytes if value is not None)
            rendered.append(f"{diagnostic.training_seed.value}:{total}")
    return ", ".join(rendered) or "0"


def _raw_message_bytes(message: CommunicationMessageDiagnostic) -> int | None:
    if message.payload_kind is ThresholdPayloadKind.KLL_SKETCH_TRANSMISSION:
        return None
    return {
        ThresholdPayloadKind.LOCAL_QUANTILE_TRANSMISSION: 8,
        ThresholdPayloadKind.THRESHOLD_TRANSMISSION: 8,
        ThresholdPayloadKind.CLUSTER_FINGERPRINT_TRANSMISSION: 40,
        ThresholdPayloadKind.GROUPED_THRESHOLD_ASSIGNMENT: 12,
        ThresholdPayloadKind.BENIGN_SUMMARY_STATISTICS: message.payload.serialized_byte_count.value,
    }.get(message.payload_kind)
