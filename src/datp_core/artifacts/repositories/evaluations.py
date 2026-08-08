from enum import StrEnum
from pathlib import Path

from datp_core.analysis.metrics.federated import (
    FederatedEvaluationArtifacts,
    FederatedEvaluationPublication,
)
from datp_core.domain.provenance import canonical_json_text


class FederatedEvaluationAssetName(StrEnum):
    DOCUMENT = "federated_evaluation.json"
    COMPLETE = "COMPLETE"


def write_federated_evaluation(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    (directory / FederatedEvaluationAssetName.DOCUMENT).write_text(
        canonical_json_text(publication.document),
        encoding="utf-8",
    )
    (directory / FederatedEvaluationAssetName.COMPLETE).write_text(
        publication.digest.value,
        encoding="utf-8",
    )
    return publication.artifacts


def federated_evaluation_is_reusable(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> bool:
    complete = directory / FederatedEvaluationAssetName.COMPLETE
    document_path = directory / FederatedEvaluationAssetName.DOCUMENT
    try:
        if not complete.is_file() or not document_path.is_file():
            return False
        if complete.read_text(encoding="utf-8").strip() != publication.digest.value:
            return False
        return document_path.read_text(encoding="utf-8") == canonical_json_text(publication.document)
    except OSError:
        return False


def load_reused_federated_evaluation(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    document_path = directory / FederatedEvaluationAssetName.DOCUMENT
    if document_path.read_text(encoding="utf-8") != canonical_json_text(publication.document):
        raise ValueError("reused federated evaluation document does not match the publication digest")
    return publication.artifacts


def rebase_federated_evaluation(
    result: FederatedEvaluationArtifacts,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    del directory
    return result
