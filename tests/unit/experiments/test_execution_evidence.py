from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.app.planning import (
    ExperimentPlan,
    PlanDisposition,
    PlannedExperiment,
    PlanReason,
    compare_materialized_execution_keys,
)
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import CoordinateStableKey
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.execution import evidence


def _plan(*keys: str) -> ExperimentPlan:
    return ExperimentPlan(
        entries=tuple(
            PlannedExperiment(
                coordinate=cast(
                    ExperimentCoordinate,
                    SimpleNamespace(stable_key=CoordinateStableKey(key), execution_key=CoordinateStableKey(key)),
                ),
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("test execution coordinate"),
            )
            for key in keys
        )
    )


def _document_path(root: Path, name: str) -> Path:
    path = root / name / FederatedEvaluationAssetName.DOCUMENT.value
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    return path


def test_materialized_execution_keys_read_persisted_document_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = _document_path(tmp_path, "first")
    second = _document_path(tmp_path, "second")
    identities = {
        first: CoordinateStableKey("experiment/first"),
        second: CoordinateStableKey("experiment/second"),
    }
    monkeypatch.setattr(
        evidence,
        "load_evaluation_document",
        lambda path: SimpleNamespace(execution_key=identities[path]),
    )

    assert evidence.materialized_execution_keys(tmp_path) == (
        CoordinateStableKey("experiment/first"),
        CoordinateStableKey("experiment/second"),
    )


def test_coordinate_completeness_rejects_missing_and_unauthorized_documents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    document = _document_path(tmp_path, "unexpected")
    monkeypatch.setattr(
        evidence,
        "load_evaluation_document",
        lambda path: SimpleNamespace(execution_key=CoordinateStableKey("experiment/unexpected")),
    )

    with pytest.raises(
        ScientificContractError,
        match="missing=experiment/expected; unauthorized=experiment/unexpected",
    ):
        evidence.require_materialized_execution_completeness(_plan("experiment/expected"), tmp_path)

    assert document.is_file()


def test_materialized_execution_keys_reject_duplicate_execution_documents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _document_path(tmp_path, "first")
    _document_path(tmp_path, "second")
    monkeypatch.setattr(
        evidence,
        "load_evaluation_document",
        lambda _path: SimpleNamespace(execution_key=CoordinateStableKey("experiment/duplicate")),
    )

    with pytest.raises(ScientificContractError, match="multiple materialized evaluation documents"):
        evidence.materialized_execution_keys(tmp_path)


def test_coordinate_comparison_uses_execution_keys_not_metric_stable_keys() -> None:
    plan = _plan("experiment/execution")

    completeness = compare_materialized_execution_keys(plan, (CoordinateStableKey("experiment/execution"),))

    assert completeness.complete
