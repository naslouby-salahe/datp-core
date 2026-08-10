from enum import StrEnum
from pathlib import Path

from datp_core.analysis.metrics.federated import FederatedEvaluationArtifacts, FederatedEvaluationPublication
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.identifiers import FileContentText
from datp_core.runtime.filesystem import write_text_atomically


class FederatedEvaluationAssetName(StrEnum):
    DOCUMENT = "federated_evaluation.json"


def write_federated_evaluation(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    write_text_atomically(
        directory / FederatedEvaluationAssetName.DOCUMENT,
        FileContentText(canonical_json_text(publication.document)),
    )
    return publication.artifacts
