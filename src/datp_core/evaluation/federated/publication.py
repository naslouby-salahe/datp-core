"""Persistence and reuse of federated evaluation artifacts."""

from enum import StrEnum
from pathlib import Path

from datp_core.domain.provenance import canonical_json_text
from datp_core.evaluation.federated.contracts import (
    FederatedEvaluationArtifacts,
    FederatedEvaluationPublication,
)


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
    document = directory / FederatedEvaluationAssetName.DOCUMENT
    try:
        return (
            complete.is_file()
            and document.is_file()
            and complete.read_text(encoding="utf-8").strip() == publication.digest.value
        )
    except OSError:
        return False


def load_reused_federated_evaluation(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    del directory
    return publication.artifacts


def rebase_federated_evaluation(
    result: FederatedEvaluationArtifacts,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    del directory
    return result
