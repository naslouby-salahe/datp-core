from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    EvidenceRole,
    FigureLabel,
    FigureTitle,
    FileContentText,
    MetricId,
    PopulationId,
    TemporalState,
)
from datp_core.core.numeric import MetricValue
from datp_core.presentation.figures import FigureSeries, FigureSpec
from datp_core.runtime.filesystem import write_text_atomically

if TYPE_CHECKING:
    from datp_core.analysis.preparation import TemporalAnalysisDocument
    from datp_core.analysis.temporal import (
        TemporalClientTrajectory,
        TemporalDeploymentProvenance,
        TemporalRecoveryResult,
    )


FIGURE_011_SOURCE_FILENAME = "figure_011_temporal_fpr_trajectories.csv"
FIGURE_012_SOURCE_FILENAME = "figure_012_temporal_threshold_movements.csv"
TEMPORAL_FIGURE_SOURCES_MANIFEST_FILENAME = "temporal_figure_sources.json"


@dataclass(frozen=True, slots=True)
class TemporalFigureSourceExports:
    fpr_trajectory_source: Path
    threshold_movement_source: Path
    manifest: Path


def temporal_publication_figures(document: TemporalAnalysisDocument) -> tuple[FigureSpec, FigureSpec]:
    fpr_series: list[FigureSeries] = []
    threshold_series: list[FigureSeries] = []
    for recovery in _ordered_recoveries(document):
        for trajectory in _ordered_trajectories(recovery):
            for state, value in _fpr_values(trajectory):
                fpr_series.append(
                    _metric_series(
                        label=FigureLabel(
                            f"client={trajectory.client_id.value};seed={trajectory.seed.value};state={state.value}"
                        ),
                        metric=MetricId.FALSE_POSITIVE_RATE,
                        value=value,
                        trajectory=trajectory,
                    )
                )

            for state, value in _threshold_values(trajectory):
                threshold_series.append(
                    _metric_series(
                        label=FigureLabel(
                            f"client={trajectory.client_id.value};seed={trajectory.seed.value};state={state.value}"
                        ),
                        metric=MetricId.THRESHOLD_VALUE,
                        value=value,
                        trajectory=trajectory,
                    )
                )
    if not fpr_series:
        fpr_series.append(_unavailable_series("no temporal per-client FPR trajectories", MetricId.FALSE_POSITIVE_RATE))
    if not threshold_series:
        threshold_series.append(
            _unavailable_series("no temporal historical/future-recalibrated thresholds", MetricId.THRESHOLD_VALUE)
        )

    return (
        FigureSpec(
            title=FigureTitle(
                "FIGURE-011 — Temporal per-client FPR trajectories "
                "(static reference, frozen future, one-shot recalibrated future; all paired seeds)"
            ),
            series=tuple(fpr_series),
        ),
        FigureSpec(
            title=FigureTitle(
                "FIGURE-012 — Temporal threshold movement "
                "(historical frozen threshold versus one-shot future recalibration; all paired seeds)"
            ),
            series=tuple(threshold_series),
        ),
    )


def export_temporal_figure_sources(
    document: TemporalAnalysisDocument,
    output_directory: Path,
) -> TemporalFigureSourceExports:
    fpr_rows = _fpr_source_rows(document)
    threshold_rows = _threshold_source_rows(document)
    fpr_path = output_directory / FIGURE_011_SOURCE_FILENAME
    threshold_path = output_directory / FIGURE_012_SOURCE_FILENAME
    manifest_path = output_directory / TEMPORAL_FIGURE_SOURCES_MANIFEST_FILENAME
    _write_csv(fpr_path, fpr_rows)
    _write_csv(threshold_path, threshold_rows)
    manifest = {
        "schema_version": "temporal_figure_sources_v1",
        "experiment": document.experiment.value,
        "population": PopulationId.EDGE_TEMPORAL_CLIENTS.value,
        "evidence_role": EvidenceRole.TEMPORAL_BOUNDARY.value,
        "threshold_method": document.threshold_method.value,
        "sources": (
            {
                "figure_id": "FIGURE-011",
                "filename": FIGURE_011_SOURCE_FILENAME,
                "row_count": len(fpr_rows),
                "metric": MetricId.FALSE_POSITIVE_RATE.value,
                "states": tuple(state.value for state in TemporalState),
                "unit": "client_x_seed_x_state",
            },
            {
                "figure_id": "FIGURE-012",
                "filename": FIGURE_012_SOURCE_FILENAME,
                "row_count": len(threshold_rows),
                "metric": "threshold_value",
                "states": (TemporalState.FROZEN_FUTURE.value, TemporalState.RECALIBRATED_FUTURE.value),
                "unit": "client_x_seed_x_policy_x_state",
            },
        ),
    }
    write_text_atomically(manifest_path, FileContentText(canonical_json_text(manifest)))
    return TemporalFigureSourceExports(
        fpr_trajectory_source=fpr_path,
        threshold_movement_source=threshold_path,
        manifest=manifest_path,
    )


def _fpr_source_rows(document: TemporalAnalysisDocument) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for recovery in _ordered_recoveries(document):
        for trajectory in _ordered_trajectories(recovery):
            for window_order, (state, value) in enumerate(_fpr_values(trajectory), start=1):
                rows.append(
                    _source_row(
                        document=document,
                        recovery=recovery,
                        trajectory=trajectory,
                        state=state,
                        value=value,
                        figure_id="FIGURE-011",
                        window_order=window_order,
                        threshold_movement=None,
                    )
                )
    return rows


def _threshold_source_rows(document: TemporalAnalysisDocument) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for recovery in _ordered_recoveries(document):
        for trajectory in _ordered_trajectories(recovery):
            for window_order, (state, value) in enumerate(_threshold_values(trajectory), start=1):
                movement = (
                    trajectory.threshold_movement_recalibrated if state is TemporalState.RECALIBRATED_FUTURE else None
                )
                rows.append(
                    _source_row(
                        document=document,
                        recovery=recovery,
                        trajectory=trajectory,
                        state=state,
                        value=value,
                        figure_id="FIGURE-012",
                        window_order=window_order,
                        threshold_movement=movement,
                    )
                )
    return rows


def _source_row(
    *,
    document: TemporalAnalysisDocument,
    recovery: TemporalRecoveryResult,
    trajectory: TemporalClientTrajectory,
    state: TemporalState,
    value: MetricValue | None,
    figure_id: str,
    window_order: int,
    threshold_movement: MetricValue | None,
) -> dict[str, str]:
    deployment = _deployment_for_state(recovery, state)
    provenance = recovery.provenance
    available = trajectory.eligible and value is not None
    return {
        "figure_id": figure_id,
        "experiment": document.experiment.value,
        "population": provenance.population.value,
        "evidence_role": document.evidence_role.value,
        "threshold_method": document.threshold_method.value,
        "policy": document.threshold_method.value,
        "metric": (MetricId.FALSE_POSITIVE_RATE.value if figure_id == "FIGURE-011" else MetricId.THRESHOLD_VALUE.value),
        "seed": str(trajectory.seed.value),
        "client_id": trajectory.client_id.value,
        "temporal_state": state.value,
        "window_order": str(window_order),
        "value": _metric_text(value) if available else "",
        "availability": (AvailabilityStatus.AVAILABLE if available else AvailabilityStatus.UNAVAILABLE).value,
        "eligible_for_fpr": str(trajectory.eligible).lower(),
        "unavailable_reason": "" if available else _trajectory_reason(trajectory),
        "threshold_movement_from_historical": _metric_text(threshold_movement) if available else "",
        "coordinate": str(deployment.coordinate),
        "calibration_score_record_count": str(len(deployment.calibration_records)),
        "evaluation_score_record_count": str(len(deployment.evaluation_records)),
    }


def _deployment_for_state(recovery: TemporalRecoveryResult, state: TemporalState) -> TemporalDeploymentProvenance:
    return {
        TemporalState.STATIC_REFERENCE: recovery.provenance.static_reference,
        TemporalState.FROZEN_FUTURE: recovery.provenance.frozen_future,
        TemporalState.RECALIBRATED_FUTURE: recovery.provenance.recalibrated_future,
    }[state]


def _ordered_recoveries(document: TemporalAnalysisDocument) -> tuple[TemporalRecoveryResult, ...]:
    return tuple(sorted((record.recovery for record in document.records), key=lambda item: item.seed.value))


def _ordered_trajectories(recovery: TemporalRecoveryResult) -> tuple[TemporalClientTrajectory, ...]:
    return tuple(sorted(recovery.client_trajectories, key=lambda item: item.client_id.value))


def _fpr_values(trajectory: TemporalClientTrajectory) -> tuple[tuple[TemporalState, MetricValue | None], ...]:
    return (
        (TemporalState.STATIC_REFERENCE, trajectory.fpr_static),
        (TemporalState.FROZEN_FUTURE, trajectory.fpr_frozen),
        (TemporalState.RECALIBRATED_FUTURE, trajectory.fpr_recalibrated),
    )


def _threshold_values(trajectory: TemporalClientTrajectory) -> tuple[tuple[TemporalState, MetricValue | None], ...]:
    return (
        (TemporalState.FROZEN_FUTURE, trajectory.threshold_frozen),
        (TemporalState.RECALIBRATED_FUTURE, trajectory.threshold_recalibrated),
    )


def _metric_series(
    *,
    label: FigureLabel,
    metric: MetricId,
    value: MetricValue | None,
    trajectory: TemporalClientTrajectory,
) -> FigureSeries:
    if trajectory.eligible and value is not None:
        return FigureSeries(label=label, metric=metric, availability=AvailabilityStatus.AVAILABLE, values=(value,))
    return FigureSeries(label=label, metric=metric, availability=AvailabilityStatus.UNAVAILABLE, values=())


def _unavailable_series(label: str, metric: MetricId) -> FigureSeries:
    return FigureSeries(label=FigureLabel(label), metric=metric, availability=AvailabilityStatus.UNAVAILABLE, values=())


def _trajectory_reason(trajectory: TemporalClientTrajectory) -> str:
    return str(
        trajectory.exclusion_reason or AnalysisReasonText("metric unavailable for temporal client-state trajectory")
    )


def _metric_text(value: MetricValue | None) -> str:
    return "" if value is None else format(value.value, ".17g")


def _write_csv(destination: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"temporal figure source requires at least one row: {destination.name}")
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=tuple(rows[0]), lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    write_text_atomically(destination, FileContentText(buffer.getvalue()))
