from collections import defaultdict
from pathlib import Path

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    ThresholdPayloadKind,
    ThresholdStageCommunicationDiagnostic,
)
from datp_core.analysis.operational.ditto import DittoIncrementalStateAndCompute
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, FileContentText
from datp_core.runtime.filesystem import write_text_atomically


def export_threshold_stage_accounting(documents: tuple[FederatedEvaluationDocument, ...], destination: Path) -> Path:
    """Publish persisted threshold-only transport and coordinator disclosure evidence."""
    _require_one_threshold_accounting_cohort(documents)
    by_method: dict[FederatedThresholdMethod, list[FederatedEvaluationDocument]] = defaultdict(list)
    for document in documents:
        by_method[document.threshold_method].append(document)
    lines = [
        "# Threshold-stage communication, storage, and runtime accounting",
        "",
        "All rows describe threshold construction after score arrays are materialized; detector scoring and disk I/O "
        "are excluded. Serialized byte counts are taken from persisted serializer-bound diagnostics.",
        "",
        "| Policy | Seeds | Upload logical fields/client | Serialized upload bytes/client (total) | "
        "Serialized response bytes/client (total) | Broadcast accounting | Threshold rounds | "
        "Raw-field bytes by seed | Runtime ms by seed (median/IQR/p95) | Coordinator observes "
        "threshold / moments / fingerprint / sketch / family / cluster assignment | Raw calibration records |",
        "| --- | ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for method, method_documents in sorted(by_method.items(), key=lambda item: item[0].value):
        ordered = tuple(sorted(method_documents, key=lambda item: item.score_coordinate.training_seed))
        diagnostics = tuple(item.diagnostics.threshold_stage_communication for item in ordered)
        if any(item is None for item in diagnostics):
            lines.append(
                f"| `{method.value}` | {len(ordered)} | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | "
                "UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | no |"
            )
            continue
        available = tuple(item for item in diagnostics if item is not None)
        kinds = frozenset(message.payload_kind for diagnostic in available for message in diagnostic.messages)
        uploads = _directional_bytes_by_seed(available, MessageDirection.CLIENT_TO_COORDINATOR, logical=True)
        responses = _directional_bytes_by_seed(available, MessageDirection.COORDINATOR_TO_CLIENT, logical=False)
        response_accounting = ", ".join(
            f"{diagnostic.training_seed.value}:{diagnostic.broadcast_accounting.value}" for diagnostic in available
        )
        rounds = ", ".join(
            f"{diagnostic.training_seed.value}:{diagnostic.communication_round_count.value}" for diagnostic in available
        )
        raw_bytes_by_seed = _raw_bytes_by_seed(available)
        runtime_by_seed = _runtime_by_seed(ordered)
        lines.append(
            f"| `{method.value}` | {len(ordered)} | {uploads[0] or '0'} | {uploads[1] or '0'} | "
            f"{responses[0] or '0'} (total={responses[1] or '0'}) | "
            f"{response_accounting or 'UNAVAILABLE'} | {rounds or '0'} | "
            f"{raw_bytes_by_seed} | {runtime_by_seed} | "
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


def export_ditto_incremental_state_and_compute(
    cost: DittoIncrementalStateAndCompute,
    destination: Path,
) -> Path:
    """Publish measured host-relative Ditto costs without presenting them as an IoT benchmark."""
    environment = cost.runtime_environment
    lines = (
        "# Ditto incremental state and compute",
        "",
        "This is a relative cost characterization on the recorded experiment host, not an IoT-device "
        "deployment benchmark.",
        "",
        f"Global coordinate: `{cost.global_coordinate.model.value}`  ",
        f"Personalized coordinate: `{cost.personalized_coordinate.model.value}`  ",
        f"Host: `{environment.host}`  ",
        f"Operating system: `{environment.operating_system}`  ",
        f"Python: `{environment.python_runtime}`  ",
        f"PyTorch: `{environment.torch_runtime}`",
        "",
        f"Serialized global-model bytes: `{cost.serialized_global_model_bytes.value}`  ",
        "Global-update communication bytes (all training rounds, upload + download): "
        f"`{cost.global_update_communication_bytes.value}`  ",
        "Measured personalized-training wall time (sum of client-round measurements): "
        f"`{cost.total_personalized_training_wall_time.value:.9g}` seconds",
        "",
        "| Client | Serialized persistent personalized-model bytes | Extra persistent state vs FedAvg bytes |",
        "| --- | ---: | ---: |",
        *(
            f"| `{item.client.client_id.value}` | {item.serialized_persistent_model_bytes.value} | "
            f"{item.extra_persistent_state_bytes_relative_to_fedavg.value} |"
            for item in cost.persistent_state_by_client
        ),
        "",
        "| Client | Round | Measured personalized-training wall time (seconds) |",
        "| --- | ---: | ---: |",
        *(
            f"| `{item.client.client_id.value}` | {item.round_number.value} | {item.wall_time.value:.9g} |"
            for item in cost.personalized_training_measurements
        ),
        "",
        "| Threshold method | Threshold-stage serialized communication bytes | Post-training rounds | "
        "Broadcast accounting |",
        "| --- | ---: | ---: | --- |",
        *(
            f"| `{item.method.value}` | {item.communication.total_serialized_bytes.value} | "
            f"{item.communication.communication_round_count.value} | {item.communication.broadcast_accounting.value} |"
            for item in cost.threshold_stage_costs
        ),
        "",
    )
    return write_text_atomically(destination, FileContentText("\n".join(lines)))


def _require_one_threshold_accounting_cohort(documents: tuple[FederatedEvaluationDocument, ...]) -> None:
    """Prevent a single accounting table from silently combining incomparable detector states."""

    if not documents:
        raise ScientificContractError(ErrorMessage("threshold-stage accounting requires evaluation documents"))
    signatures = {_score_cohort_signature(document) for document in documents}
    if len(signatures) != 1:
        raise ScientificContractError(
            ErrorMessage(
                "threshold-stage accounting requires one population, split, preprocessing, and detector cohort"
            )
        )
    cells = tuple((document.threshold_method, document.score_coordinate.training_seed) for document in documents)
    if len(cells) != len(frozenset(cells)):
        raise ScientificContractError(ErrorMessage("threshold-stage accounting cannot repeat a policy/seed cell"))


def _score_cohort_signature(document: FederatedEvaluationDocument) -> tuple[object, ...]:
    coordinate = document.score_coordinate
    return (
        coordinate.population,
        coordinate.split_protocol,
        coordinate.preprocessing_identity,
        coordinate.model,
        coordinate.model_coefficient,
    )


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


def _directional_bytes_by_seed(
    diagnostics: tuple[ThresholdStageCommunicationDiagnostic, ...],
    direction: MessageDirection,
    *,
    logical: bool,
) -> tuple[str, str]:
    rendered: list[str] = []
    total_by_seed: list[str] = []
    for diagnostic in diagnostics:
        messages = tuple(item for item in diagnostic.messages if item.direction is direction)
        by_client: dict[str, int] = defaultdict(int)
        for message in messages:
            if message.client is None:
                raise ScientificContractError(ErrorMessage("threshold-stage messages require a client identity"))
            value = message.payload.logical_element_count.value if logical else message.estimated_serialized_bytes.value
            by_client[message.client.client_id.value] += value
        per_client = ";".join(f"{client}:{value}" for client, value in sorted(by_client.items())) or "0"
        total = sum(by_client.values())
        rendered.append(f"{diagnostic.training_seed.value}:{per_client}")
        total_by_seed.append(f"{diagnostic.training_seed.value}:{total}")
    return ", ".join(rendered), ", ".join(total_by_seed)


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


def _runtime_by_seed(documents: tuple[FederatedEvaluationDocument, ...]) -> str:
    rendered: list[str] = []
    for document in documents:
        timing = document.diagnostics.threshold_construction_runtime
        if timing is None:
            rendered.append(f"{document.score_coordinate.training_seed.value}:UNAVAILABLE")
            continue
        rendered.append(
            f"{document.score_coordinate.training_seed.value}:"
            f"{timing.median_milliseconds.value:.6g}/"
            f"{timing.interquartile_range_milliseconds.value:.6g}/"
            f"{timing.p95_milliseconds.value:.6g}"
        )
    return ", ".join(rendered)
