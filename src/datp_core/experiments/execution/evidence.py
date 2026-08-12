from pathlib import Path

from pydantic import ValidationError

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, MetricId
from datp_core.core.numeric import MetricValue


def load_evaluation_document(path: Path) -> FederatedEvaluationDocument:

    try:
        if not path.is_file():
            raise ScientificContractError(
                ErrorMessage(f"completed evaluation document is missing: {path}"),
                subject=ContractSubject.ARTIFACT_PATH,
            )
        document = FederatedEvaluationDocument.model_validate_json(path.read_text(encoding="utf-8"))
        return document
    except (OSError, ValidationError, ValueError) as error:
        raise ScientificContractError(
            ErrorMessage(f"completed evaluation document is unreadable or invalid: {path}"),
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error


def population_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(ErrorMessage(f"required metric is unavailable: {metric.value}"))
    return result.value
