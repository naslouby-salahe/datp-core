"""Planner-owned semantic layout for one experiment output directory."""

from __future__ import annotations

import re

from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.jobs import StageOutput

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def _segment(value: object | None, *, fallback: str) -> str:
    text = fallback if value is None else str(getattr(value, "value", value))
    if not _SAFE_SEGMENT.fullmatch(text):
        raise ValueError(f"Unsafe semantic output path component: {text!r}")
    return text


def _number(value: float | None, *, name: str) -> str | None:
    return None if value is None else f"{name}-{value:.17g}"


def cell_directory(context: StageJobContext) -> str:
    """Return the complete semantic coordinate for a seed/model cell."""

    parts = [
        f"population-{_segment(context.population_id, fallback='experiment')}",
        f"condition-{_segment(context.partition_condition, fallback='default')}",
        f"seed-{_segment(context.seed, fallback='aggregate')}",
    ]
    for value in (
        _number(context.federated_proximal_mu, name="mu"),
        _number(context.ditto_proximal_weight, name="ditto-weight"),
    ):
        if value is not None:
            parts.append(value)
    return "/".join(parts)


def evaluation_directory(context: StageJobContext) -> str:
    parts = [
        f"evaluation-{_segment(context.evaluation_label, fallback='default')}",
        f"policy-{_segment(context.threshold_policy_id, fallback='default')}",
        cell_directory(context),
    ]
    for value in (
        _number(context.threshold_quantile, name="quantile"),
        _number(context.shrinkage_weight, name="shrinkage"),
        _number(context.federated_summary_fixed_k, name="fixed-k"),
    ):
        if value is not None:
            parts.append(value)
    if context.fingerprint_features is not None:
        parts.append("features-" + "+".join(_segment(item, fallback="none") for item in context.fingerprint_features))
    if context.calibration_sample_count is not None:
        parts.append(f"calibration-n-{context.calibration_sample_count}-rep-{context.calibration_replicate}")
    if context.recalibration_mode is not None:
        parts.append(f"recalibration-{_segment(context.recalibration_mode, fallback='none')}")
    return "/".join(parts)


def output(name: str, relative_path: str) -> StageOutput:
    return StageOutput(name=name, relative_path=relative_path)


def shared_output_path(*, directory: str, ordinal: int, output_name: str, source_path: str) -> str:
    """Return a stable campaign-owned location without encoding a sharing key."""

    suffix = source_path.rsplit(".", maxsplit=1)
    extension = f".{suffix[1]}" if len(suffix) == 2 else ""
    return f"shared/{directory}/{ordinal:04d}/{output_name}{extension}"
