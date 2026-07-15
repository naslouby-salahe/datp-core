from dataclasses import fields
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

import pytest

from datp_core.application.ports.telemetry import EVENT_DETAIL_BINDINGS, RunPlannedDetail
from datp_core.domain.artifacts.references import ArtifactRef


@pytest.mark.architecture
def test_telemetry_detail_vocabulary_excludes_forbidden_payload_types() -> None:
    for binding in EVENT_DETAIL_BINDINGS:
        detail_type = binding.detail_type
        hints = get_type_hints(detail_type)
        for field in fields(detail_type):
            annotation = hints[field.name]
            assert field.name != "configuration"
            assert "secret" not in field.name
            assert not _contains_forbidden_payload_type(annotation)

    run_planned_hints = get_type_hints(RunPlannedDetail)
    assert run_planned_hints["resolved_configuration"] is ArtifactRef


@pytest.mark.architecture
def test_structlog_is_confined_to_the_telemetry_adapter() -> None:
    source = (
        Path(__file__).parents[2] / "src" / "datp_core" / "infrastructure" / "telemetry" / "structured_events.py"
    ).read_text()

    assert "import structlog" in source
    assert "datp_core.domain" not in source


def _contains_forbidden_payload_type(annotation: object) -> bool:
    contains_forbidden_argument = any(_contains_forbidden_payload_type(argument) for argument in get_args(annotation))
    return contains_forbidden_argument or get_origin(annotation) in (
        list,
        tuple,
        dict,
    )
