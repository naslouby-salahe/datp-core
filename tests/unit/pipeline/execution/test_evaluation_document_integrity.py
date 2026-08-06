"""Evaluation document loading requires COMPLETE digest binding."""

from pathlib import Path

import pytest

from datp_core.domain.errors import ScientificContractError
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.pipeline.execution.evidence import load_evaluation_document


def test_load_evaluation_document_requires_complete_marker(tmp_path: Path) -> None:
    document_path = tmp_path / FederatedEvaluationAssetName.DOCUMENT
    document_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ScientificContractError, match="COMPLETE marker is missing"):
        load_evaluation_document(document_path)


def test_load_evaluation_document_rejects_missing_document(tmp_path: Path) -> None:
    document_path = tmp_path / FederatedEvaluationAssetName.DOCUMENT
    with pytest.raises(ScientificContractError, match="document is missing"):
        load_evaluation_document(document_path)


def test_load_evaluation_document_rejects_invalid_document_with_marker(tmp_path: Path) -> None:
    document_path = tmp_path / FederatedEvaluationAssetName.DOCUMENT
    complete_path = tmp_path / FederatedEvaluationAssetName.COMPLETE
    document_path.write_text('{"not":"a valid federated evaluation document"}', encoding="utf-8")
    complete_path.write_text("not-a-matching-digest", encoding="utf-8")
    with pytest.raises(ScientificContractError, match="unreadable or invalid|does not match"):
        load_evaluation_document(document_path)
