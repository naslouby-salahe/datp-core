"""Validation of fixed-score evidence and threshold-policy invariance."""

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ContractSubject, MetricId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.base import floats_absolutely_close
from datp_core.domain.values.ratios import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE, AbsoluteTolerance
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.fixed_score.checksums import (
    ClientChecksumField,
    aggregate_client_checksum,
    evaluation_score_order_checksum,
)
from datp_core.evaluation.fixed_score.contracts import ClientAurocEvidence, FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, MetricAvailability, MetricStatus, metric_by_id
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.inference import FixedScoreInvariant, ScoreArtifactManifest

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


def validate_evaluation_evidence(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    invariant = FixedScoreInvariant.from_manifest(manifest)
    _validate_manifest_binding(evidence, manifest, invariant)
    _validate_population_binding(evidence, cohort, clients)
    _validate_held_out_rows(evidence, manifest, clients)
    _validate_aurocs(evidence, clients)


def validate_fixed_score_controls(
    first: FixedScoreEvidence,
    second: FixedScoreEvidence,
    *,
    auroc_absolute_tolerance: AbsoluteTolerance,
) -> None:
    """Reject every changed fixed input; threshold policy is the sole difference."""
    if first.threshold_method is second.threshold_method:
        raise ScientificContractError(
            "fixed-score comparison requires distinct threshold methods",
            subject=ContractSubject.THRESHOLD_METHOD,
        )
    _require_equal(
        first.detector.coordinate,
        second.detector.coordinate,
        ContractSubject.COORDINATE,
        "training coordinate",
    )
    _require_equal(
        first.calibration.role,
        second.calibration.role,
        ContractSubject.SPLIT,
        "calibration partition role",
    )
    for left, right, subject, name in (
        (first.detector.model_checksum, second.detector.model_checksum, ContractSubject.SCORES, "model checksum"),
        (
            first.detector.preprocessing_checksum,
            second.detector.preprocessing_checksum,
            ContractSubject.PREPROCESSING,
            "preprocessing checksum",
        ),
        (
            first.detector.selected_checkpoint_checksum,
            second.detector.selected_checkpoint_checksum,
            ContractSubject.CHECKPOINT_CANDIDATES,
            "selected-checkpoint checksum",
        ),
        (
            first.calibration.score_checksum,
            second.calibration.score_checksum,
            ContractSubject.SCORES,
            "calibration-score checksum",
        ),
        (
            first.evaluation.score_checksum,
            second.evaluation.score_checksum,
            ContractSubject.SCORES,
            "evaluation-score checksum",
        ),
        (
            first.evaluation.label_checksum,
            second.evaluation.label_checksum,
            ContractSubject.LABEL,
            "evaluation-label checksum",
        ),
        (
            first.population.client_inventory_checksum,
            second.population.client_inventory_checksum,
            ContractSubject.CLIENT_IDENTITY,
            "client population",
        ),
        (
            first.population.eligibility_cohort_checksum,
            second.population.eligibility_cohort_checksum,
            ContractSubject.CLIENT_IDENTITY,
            "eligibility cohort",
        ),
        (
            first.evaluation.source_row_checksum,
            second.evaluation.source_row_checksum,
            ContractSubject.ROWS,
            "source-row identities",
        ),
        (
            first.evaluation.score_order_checksum,
            second.evaluation.score_order_checksum,
            ContractSubject.SCORES,
            "score ordering",
        ),
    ):
        _require_equal(left, right, subject, name)
    _require_auroc_invariance(
        first.evaluation.aurocs,
        second.evaluation.aurocs,
        auroc_absolute_tolerance,
    )


def _validate_manifest_binding(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    invariant: FixedScoreInvariant,
) -> None:
    if evidence.detector.coordinate != manifest.coordinate:
        raise ScientificContractError("fixed-score evidence must match the score coordinate")
    if not manifest.records_for(evidence.calibration.role):
        raise ScientificContractError("fixed-score evidence calibration partition is unavailable in the score manifest")
    bindings = (
        ("model", evidence.detector.model_checksum, invariant.model_checksum),
        ("preprocessing", evidence.detector.preprocessing_checksum, invariant.preprocessing_state_set_checksum),
        ("checkpoint", evidence.detector.selected_checkpoint_checksum, manifest.checkpoint_checksum),
        (
            "calibration score",
            evidence.calibration.score_checksum,
            manifest.score_set_checksum(evidence.calibration.role),
        ),
        ("evaluation score", evidence.evaluation.score_checksum, invariant.evaluation_score_set_checksum),
    )
    for name, observed, expected in bindings:
        if observed != expected:
            raise ScientificContractError(f"fixed-score evidence {name} checksum does not match the score manifest")


def _validate_population_binding(
    evidence: FixedScoreEvidence,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    expected_population = canonical_checksum(tuple(sorted(client.client for client in clients)))
    if evidence.population.client_inventory_checksum != expected_population:
        raise ScientificContractError("fixed-score evidence client population checksum does not match evaluation")
    if evidence.population.eligibility_cohort_checksum != canonical_checksum(cohort):
        raise ScientificContractError("fixed-score evidence eligibility cohort checksum does not match evaluation")


def _validate_held_out_rows(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    if evidence.evaluation.score_order_checksum != evaluation_score_order_checksum(manifest):
        raise ScientificContractError("fixed-score evidence score ordering checksum does not match evaluation")
    expected_labels = aggregate_client_checksum(clients, ClientChecksumField.EVALUATION_LABEL)
    expected_rows = aggregate_client_checksum(clients, ClientChecksumField.SOURCE_ROW)
    labels_mismatch = evidence.evaluation.label_checksum != expected_labels
    rows_mismatch = evidence.evaluation.source_row_checksum != expected_rows
    if labels_mismatch or rows_mismatch:
        raise ScientificContractError("fixed-score evidence label or source-row checksum does not match evaluation")


def _validate_aurocs(evidence: FixedScoreEvidence, clients: tuple[ClientMetricResult, ...]) -> None:
    observed = tuple((client.client, metric_by_id(client.metrics, MetricId.AUROC)) for client in clients)
    if tuple(item.client for item in evidence.evaluation.aurocs) != tuple(client for client, _ in observed):
        raise ScientificContractError("fixed-score AUROC evidence client order does not match evaluation")
    for expected_item, (_, observed_outcome) in zip(evidence.evaluation.aurocs, observed, strict=True):
        _require_matching_auroc(expected_item.outcome, observed_outcome)


def _require_equal(left: object, right: object, subject: ContractSubject, name: str) -> None:
    if left != right:
        raise ScientificContractError(f"fixed-score control failed: {name} differs", subject=subject)


def _require_auroc_invariance(
    first: tuple[ClientAurocEvidence, ...],
    second: tuple[ClientAurocEvidence, ...],
    tolerance: AbsoluteTolerance,
) -> None:
    if tuple(item.client for item in first) != tuple(item.client for item in second):
        raise ScientificContractError(
            "fixed-score control failed: AUROC clients differ",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    for left, right in zip(first, second, strict=True):
        if left.outcome.status is not right.outcome.status:
            raise ScientificContractError(
                "fixed-score control failed: AUROC availability differs",
                subject=ContractSubject.HELD_OUT_METRICS,
            )
        if left.outcome.status is not MetricStatus.AVAILABLE:
            if left.outcome != right.outcome:
                raise ScientificContractError(
                    "fixed-score control failed: AUROC unavailable outcome differs",
                    subject=ContractSubject.HELD_OUT_METRICS,
                )
            continue
        if left.outcome.value is None or right.outcome.value is None:
            raise RuntimeError("available AUROC evidence must contain values")
        if not floats_absolutely_close(left.outcome.value.value, right.outcome.value.value, tolerance.value):
            raise ScientificContractError(
                "fixed-score control failed: AUROC differs",
                subject=ContractSubject.HELD_OUT_METRICS,
            )


def _require_matching_auroc(expected: MetricAvailability, observed: MetricAvailability) -> None:
    if expected.status is not observed.status:
        raise ScientificContractError("fixed-score AUROC availability does not match held-out evaluation")
    if expected.status is MetricStatus.AVAILABLE:
        if expected.value is None or observed.value is None:
            raise RuntimeError("available AUROC evidence must contain values")
        if not floats_absolutely_close(
            expected.value.value,
            observed.value.value,
            NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value,
        ):
            raise ScientificContractError("fixed-score AUROC evidence does not match held-out evaluation")
    elif expected != observed:
        raise ScientificContractError("fixed-score AUROC unavailable outcome does not match held-out evaluation")
