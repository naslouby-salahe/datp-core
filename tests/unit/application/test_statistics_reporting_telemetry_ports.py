from dataclasses import fields, is_dataclass
from inspect import signature
from types import UnionType
from typing import Protocol, Union, get_args, get_origin, get_type_hints

import pytest

from datp_core.application.ports import reporting, statistics, telemetry
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.experiments.identities import CellId, ExperimentId
from datp_core.domain.runtime.admissibility import GpuIndex
from datp_core.domain.runtime.policies import PipelineStage, RunStatus, WorkerRole
from datp_core.domain.runtime.seeds import Seed


def _artifact_reference() -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{'a' * 64}"),
        artifact_type=ArtifactType.RESOLVED_CONFIGURATION,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _event_context() -> telemetry.EventContext:
    return telemetry.EventContext(
        run_id="run-telemetry-test",
        experiment_id=ExperimentId(value="E-X1"),
        cell_id=CellId(value=f"E-X1#{'c' * 16}"),
        stage=PipelineStage.ANALYZE,
        stage_fingerprint=StageFingerprint(value="d" * 64),
        seed=Seed(value=1),
        worker_role=WorkerRole.MAIN,
        process_id=1,
        gpu_index=GpuIndex(value=0),
        elapsed_seconds=1.0,
        peak_ram_bytes=1024,
        peak_vram_bytes=2048,
    )


def _event_details() -> tuple[telemetry.EventDetail, ...]:
    artifact = _artifact_reference()
    fingerprint = StageFingerprint(value="e" * 64)
    seed = Seed(value=2)
    return (
        telemetry.RunPlannedDetail(resolved_configuration=artifact, planned_stage_count=1),
        telemetry.StageLifecycleDetail(
            stage=PipelineStage.ANALYZE,
            previous_status=RunStatus.READY,
            current_status=RunStatus.RUNNING,
        ),
        telemetry.ArtifactEventDetail(artifact=artifact),
        telemetry.ResourceEventDetail(available_ram_bytes=1024, available_vram_bytes=2048),
        telemetry.DeterminismEventDetail(expected_seed=seed, observed_seed=seed),
        telemetry.LineageEventDetail(expected_fingerprint=fingerprint, observed_fingerprint=fingerprint),
        telemetry.FederatedRoundEventDetail(
            round_number=1,
            expected_client_count=2,
            completed_client_count=2,
            failed_client_count=0,
            duration_seconds=1.0,
            peak_ram_bytes=1024,
            peak_vram_bytes=2048,
            recovery_status=RunStatus.RECOVERED,
        ),
        telemetry.HeartbeatEventDetail(last_progress_stage=PipelineStage.ANALYZE, staleness_deadline_seconds=2.0),
        telemetry.RecoveryEventDetail(compatible_checkpoint=artifact, last_completed_round=1),
        telemetry.TestProfileDetail(profile_name="unit", suite_name="unit"),
    )


def _detail_for(detail_type: telemetry.EventDetailType) -> telemetry.EventDetail:
    for detail in _event_details():
        if type(detail) is detail_type:
            return detail
    raise AssertionError(f"missing representative detail for {detail_type.__name__}")


def test_statistics_and_reporting_protocols_have_one_named_request_and_result() -> None:
    for port, method_name in (
        (statistics.StatisticalProcedureRunner, "run"),
        (reporting.ReportRenderer, "render"),
    ):
        assert issubclass(port, Protocol)
        method = getattr(port, method_name)
        assert tuple(signature(method).parameters) == ("self", "request")
        annotations = get_type_hints(method)
        assert set(annotations) == {"request", "return"}
        assert is_dataclass(annotations["request"])

    assert statistics.StatisticalProcedureRunner.run.__annotations__["return"] is statistics.StatisticalAnalysisResult
    assert reporting.ReportRenderer.render.__annotations__["return"] is reporting.RenderedReportArtifact


def test_telemetry_vocabulary_matches_the_complete_architecture_contract() -> None:
    assert tuple(telemetry.LogEventKind) == (
        telemetry.LogEventKind.RUN_PLANNED,
        telemetry.LogEventKind.RUN_STARTED,
        telemetry.LogEventKind.RUN_COMPLETED,
        telemetry.LogEventKind.RUN_FAILED,
        telemetry.LogEventKind.STAGE_STARTED,
        telemetry.LogEventKind.STAGE_REUSED,
        telemetry.LogEventKind.STAGE_COMPLETED,
        telemetry.LogEventKind.STAGE_BLOCKED,
        telemetry.LogEventKind.STAGE_FAILED,
        telemetry.LogEventKind.STAGE_HEARTBEAT,
        telemetry.LogEventKind.FEDERATED_ROUND_STARTED,
        telemetry.LogEventKind.FEDERATED_ROUND_COMPLETED,
        telemetry.LogEventKind.FEDERATED_ROUND_FAILED,
        telemetry.LogEventKind.RECOVERY_CHECKPOINT_COMMITTED,
        telemetry.LogEventKind.RESOURCE_PRESSURE_DETECTED,
        telemetry.LogEventKind.STAGE_PAUSED,
        telemetry.LogEventKind.STAGE_RESUMED,
        telemetry.LogEventKind.ARTIFACT_LOCK_ACQUIRED,
        telemetry.LogEventKind.ARTIFACT_REUSED,
        telemetry.LogEventKind.ARTIFACT_WRITTEN,
        telemetry.LogEventKind.ARTIFACT_REJECTED,
        telemetry.LogEventKind.RESOURCE_PREFLIGHT_COMPLETED,
        telemetry.LogEventKind.CUDA_OUT_OF_MEMORY,
        telemetry.LogEventKind.DETERMINISM_VIOLATION,
        telemetry.LogEventKind.LINEAGE_MISMATCH,
        telemetry.LogEventKind.TEST_PROFILE_STARTED,
        telemetry.LogEventKind.TEST_PROFILE_COMPLETED,
    )
    assert tuple(telemetry.LogSink) == (telemetry.LogSink.CONSOLE, telemetry.LogSink.JSONL_FILE)
    assert tuple(telemetry.LogFormat) == (telemetry.LogFormat.HUMAN_READABLE, telemetry.LogFormat.JSON)


def test_every_event_kind_has_one_exhaustive_detail_binding() -> None:
    bound_kinds = tuple(binding.kind for binding in telemetry.EVENT_DETAIL_BINDINGS)
    assert len(bound_kinds) == len(set(bound_kinds))
    assert set(bound_kinds) == set(telemetry.LogEventKind)

    for binding in telemetry.EVENT_DETAIL_BINDINGS:
        assert telemetry.expected_event_detail_type(binding.kind) is binding.detail_type
        assert is_dataclass(binding.detail_type)


def test_every_event_detail_is_safe_even_through_nested_dataclass_fields() -> None:
    inspected_types: set[type[object]] = set()
    forbidden_field_fragments = ("array", "per_sample", "secret", "dataset_row", "configuration_dump")

    for detail_type in {binding.detail_type for binding in telemetry.EVENT_DETAIL_BINDINGS}:
        _assert_safe_event_detail_annotation(
            annotation=detail_type,
            inspected_types=inspected_types,
            forbidden_field_fragments=forbidden_field_fragments,
        )


def _assert_safe_event_detail_annotation(
    *,
    annotation: object,
    inspected_types: set[type[object]],
    forbidden_field_fragments: tuple[str, ...],
) -> None:
    origin = get_origin(annotation)
    if origin in (UnionType, Union):
        _assert_safe_event_detail_union(
            union_members=get_args(annotation),
            inspected_types=inspected_types,
            forbidden_field_fragments=forbidden_field_fragments,
        )
        return
    assert origin not in (dict, list, set, frozenset)
    _assert_safe_event_detail_dataclass(
        annotation=annotation,
        inspected_types=inspected_types,
        forbidden_field_fragments=forbidden_field_fragments,
    )


def _assert_safe_event_detail_union(
    *,
    union_members: tuple[object, ...],
    inspected_types: set[type[object]],
    forbidden_field_fragments: tuple[str, ...],
) -> None:
    for union_member in union_members:
        _assert_safe_event_detail_annotation(
            annotation=union_member,
            inspected_types=inspected_types,
            forbidden_field_fragments=forbidden_field_fragments,
        )


def _assert_safe_event_detail_dataclass(
    *,
    annotation: object,
    inspected_types: set[type[object]],
    forbidden_field_fragments: tuple[str, ...],
) -> None:
    if not isinstance(annotation, type):
        return
    if not is_dataclass(annotation):
        return
    if annotation in inspected_types:
        return
    inspected_types.add(annotation)
    for field in fields(annotation):
        assert not any(fragment in field.name.casefold() for fragment in forbidden_field_fragments)
        _assert_safe_event_detail_annotation(
            annotation=get_type_hints(annotation)[field.name],
            inspected_types=inspected_types,
            forbidden_field_fragments=forbidden_field_fragments,
        )


@pytest.mark.contract
def test_event_sink_dispatches_every_constructed_event_variant() -> None:
    published: list[telemetry.StructuredEvent] = []

    class RecordingEventSink:
        def publish(self, event: telemetry.StructuredEvent) -> None:
            published.append(event)

    sink = RecordingEventSink()
    for binding in telemetry.EVENT_DETAIL_BINDINGS:
        event = telemetry.StructuredEvent(
            kind=binding.kind,
            context=_event_context(),
            detail=_detail_for(binding.detail_type),
            status=RunStatus.RUNNING,
            error_code=None,
            message="diagnostic event",
        )
        sink.publish(event)

    assert len(published) == len(telemetry.LogEventKind)


def test_structured_event_rejects_an_incompatible_detail() -> None:
    context = _event_context()
    detail = telemetry.ArtifactEventDetail(artifact=_artifact_reference())

    with pytest.raises(ValueError, match="event detail does not match"):
        telemetry.StructuredEvent(
            kind=telemetry.LogEventKind.RUN_PLANNED,
            context=context,
            detail=detail,
            status=RunStatus.PLANNED,
            error_code=None,
            message="invalid diagnostic event",
        )


def test_diagnostic_event_publish_failures_are_isolated() -> None:
    class FailingEventSink:
        def publish(self, event: telemetry.StructuredEvent) -> None:
            raise RuntimeError(event.message)

    binding = telemetry.EVENT_DETAIL_BINDINGS[0]
    telemetry.publish_diagnostic_event(
        event_sink=FailingEventSink(),
        event=telemetry.StructuredEvent(
            kind=binding.kind,
            context=_event_context(),
            detail=_detail_for(binding.detail_type),
            status=RunStatus.PLANNED,
            error_code=None,
            message="diagnostic failure",
        ),
    )
