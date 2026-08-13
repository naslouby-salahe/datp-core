from pathlib import Path

from pydantic import ValidationError

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.app.planning import CoordinateCompleteness, ExperimentPlan, compare_materialized_execution_keys
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, CoordinateStableKey, MetricId
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


def materialized_execution_keys(output_root: Path) -> tuple[CoordinateStableKey, ...]:
    document_paths = tuple(sorted(output_root.rglob(FederatedEvaluationAssetName.DOCUMENT.value)))
    keys_by_document = tuple((path, load_evaluation_document(path).execution_key) for path in document_paths)
    paths_by_key: dict[CoordinateStableKey, list[Path]] = {}
    for path, key in keys_by_document:
        paths_by_key.setdefault(key, []).append(path)
    duplicates = tuple((key, tuple(paths)) for key, paths in paths_by_key.items() if len(paths) != 1)
    if duplicates:
        details = "; ".join(f"{key}: {', '.join(str(path) for path in paths)}" for key, paths in sorted(duplicates))
        raise ScientificContractError(
            ErrorMessage(f"execution coordinate has multiple materialized evaluation documents: {details}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return tuple(key for _, key in keys_by_document)


def require_materialized_execution_completeness(
    plan: ExperimentPlan,
    output_root: Path,
) -> CoordinateCompleteness:
    completeness = compare_materialized_execution_keys(plan, materialized_execution_keys(output_root))
    if completeness.complete:
        return completeness
    missing = ", ".join(completeness.missing_execution_keys) or "none"
    unauthorized = ", ".join(completeness.unauthorized_execution_keys) or "none"
    raise ScientificContractError(
        ErrorMessage(
            f"materialized execution coordinates are incomplete: missing={missing}; unauthorized={unauthorized}"
        ),
        subject=ContractSubject.ARTIFACT_PATH,
    )


def population_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(ErrorMessage(f"required metric is unavailable: {metric.value}"))
    return result.value
