from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.fixed_score import ClientAurocEvidence, FixedScoreEvidence
from datp_core.analysis.metrics.fixed_score_checksums import (
    ClientChecksumField,
    aggregate_client_checksum,
    evaluation_score_order_checksum,
)
from datp_core.analysis.metrics.models import ClientMetricResult, MetricAvailability, MetricStatus, metric_by_id
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, MetricId, ValidationLabel
from datp_core.core.numeric import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE, AbsoluteTolerance, floats_absolutely_close
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import FixedScoreInvariant, ScoreArtifactManifest
from datp_core.detector.training.models import FederatedTrainingCoordinate

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
            ErrorMessage("fixed-score comparison requires distinct threshold methods"),
            subject=ContractSubject.THRESHOLD_METHOD,
        )
    _require_equal(
        first.detector.coordinate,
        second.detector.coordinate,
        ContractSubject.COORDINATE,
        ValidationLabel("training coordinate"),
    )
    _require_equal(
        first.calibration.role,
        second.calibration.role,
        ContractSubject.SPLIT,
        ValidationLabel("calibration partition role"),
    )
    for left, right, subject, name in (
        (
            first.detector.model_checksum,
            second.detector.model_checksum,
            ContractSubject.SCORES,
            ValidationLabel("model checksum"),
        ),
        (
            first.detector.preprocessing_checksum,
            second.detector.preprocessing_checksum,
            ContractSubject.PREPROCESSING,
            ValidationLabel("preprocessing checksum"),
        ),
        (
            first.detector.selected_checkpoint_checksum,
            second.detector.selected_checkpoint_checksum,
            ContractSubject.CHECKPOINT_CANDIDATES,
            ValidationLabel("selected-checkpoint checksum"),
        ),
        (
            first.calibration.score_checksum,
            second.calibration.score_checksum,
            ContractSubject.SCORES,
            ValidationLabel("calibration-score checksum"),
        ),
        (
            first.evaluation.score_checksum,
            second.evaluation.score_checksum,
            ContractSubject.SCORES,
            ValidationLabel("evaluation-score checksum"),
        ),
        (
            first.evaluation.label_checksum,
            second.evaluation.label_checksum,
            ContractSubject.LABEL,
            ValidationLabel("evaluation-label checksum"),
        ),
        (
            first.population.client_inventory_checksum,
            second.population.client_inventory_checksum,
            ContractSubject.CLIENT_IDENTITY,
            ValidationLabel("client population"),
        ),
        (
            first.population.eligibility_cohort_checksum,
            second.population.eligibility_cohort_checksum,
            ContractSubject.CLIENT_IDENTITY,
            ValidationLabel("eligibility cohort"),
        ),
        (
            first.evaluation.source_row_checksum,
            second.evaluation.source_row_checksum,
            ContractSubject.ROWS,
            ValidationLabel("source-row identities"),
        ),
        (
            first.evaluation.score_order_checksum,
            second.evaluation.score_order_checksum,
            ContractSubject.SCORES,
            ValidationLabel("score ordering"),
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
        raise ScientificContractError(ErrorMessage("fixed-score evidence must match the score coordinate"))
    if not manifest.records_for(evidence.calibration.role):
        raise ScientificContractError(
            ErrorMessage("fixed-score evidence calibration partition is unavailable in the score manifest")
        )
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
            raise ScientificContractError(
                ErrorMessage(f"fixed-score evidence {name} checksum does not match the score manifest")
            )


def _validate_population_binding(
    evidence: FixedScoreEvidence,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    expected_population = canonical_checksum(tuple(sorted([client.client for client in clients])))
    if evidence.population.client_inventory_checksum != expected_population:
        raise ScientificContractError(
            ErrorMessage("fixed-score evidence client population checksum does not match evaluation")
        )
    if evidence.population.eligibility_cohort_checksum != canonical_checksum(cohort):
        raise ScientificContractError(
            ErrorMessage("fixed-score evidence eligibility cohort checksum does not match evaluation")
        )


def _validate_held_out_rows(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    if evidence.evaluation.score_order_checksum != evaluation_score_order_checksum(manifest):
        raise ScientificContractError(
            ErrorMessage("fixed-score evidence score ordering checksum does not match evaluation")
        )

    expected_labels = aggregate_client_checksum(clients, ClientChecksumField.EVALUATION_LABEL)
    if evidence.evaluation.label_checksum != expected_labels:
        raise ScientificContractError(
            ErrorMessage("fixed-score evidence label or source-row checksum does not match evaluation")
        )

    expected_rows = aggregate_client_checksum(clients, ClientChecksumField.SOURCE_ROW)
    if evidence.evaluation.source_row_checksum != expected_rows:
        raise ScientificContractError(
            ErrorMessage("fixed-score evidence label or source-row checksum does not match evaluation")
        )


def _validate_aurocs(evidence: FixedScoreEvidence, clients: tuple[ClientMetricResult, ...]) -> None:
    if len(evidence.evaluation.aurocs) != len(clients):
        raise ScientificContractError(ErrorMessage("fixed-score AUROC evidence client order does not match evaluation"))

    for expected_item, client in zip(evidence.evaluation.aurocs, clients, strict=True):
        if expected_item.client != client.client:
            raise ScientificContractError(
                ErrorMessage("fixed-score AUROC evidence client order does not match evaluation")
            )
        observed_outcome = metric_by_id(client.metrics, MetricId.AUROC)
        _require_matching_auroc(expected_item.outcome, observed_outcome)


def _require_equal[ValueT](
    left: ValueT,
    right: ValueT,
    subject: ContractSubject,
    name: ValidationLabel,
) -> None:
    if left != right:
        raise ScientificContractError(ErrorMessage(f"fixed-score control failed: {name} differs"), subject=subject)


def _require_auroc_invariance(
    first: tuple[ClientAurocEvidence, ...],
    second: tuple[ClientAurocEvidence, ...],
    tolerance: AbsoluteTolerance,
) -> None:
    if len(first) != len(second):
        raise ScientificContractError(
            ErrorMessage("fixed-score control failed: AUROC clients differ"),
            subject=ContractSubject.CLIENT_IDENTITY,
        )

    for left, right in zip(first, second, strict=True):
        _require_auroc_pair_invariance(left, right, tolerance)


def _require_auroc_pair_invariance(
    left: ClientAurocEvidence,
    right: ClientAurocEvidence,
    tolerance: AbsoluteTolerance,
) -> None:
    if left.client != right.client:
        raise ScientificContractError(
            ErrorMessage("fixed-score control failed: AUROC clients differ"),
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if left.outcome.status is not right.outcome.status:
        raise ScientificContractError(
            ErrorMessage("fixed-score control failed: AUROC availability differs"),
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if left.outcome.status is not MetricStatus.AVAILABLE:
        if left.outcome != right.outcome:
            raise ScientificContractError(
                ErrorMessage("fixed-score control failed: AUROC unavailable outcome differs"),
                subject=ContractSubject.HELD_OUT_METRICS,
            )
        return
    if left.outcome.value is None or right.outcome.value is None:
        raise RuntimeError("available AUROC evidence must contain values")
    if not floats_absolutely_close(left.outcome.value.value, right.outcome.value.value, tolerance.value):
        raise ScientificContractError(
            ErrorMessage("fixed-score control failed: AUROC differs"),
            subject=ContractSubject.HELD_OUT_METRICS,
        )


def _require_matching_auroc(expected: MetricAvailability, observed: MetricAvailability) -> None:
    if expected.status is not observed.status:
        raise ScientificContractError(ErrorMessage("fixed-score AUROC availability does not match held-out evaluation"))
    if expected.status is MetricStatus.AVAILABLE:
        if expected.value is None or observed.value is None:
            raise RuntimeError("available AUROC evidence must contain values")
        if not floats_absolutely_close(
            expected.value.value,
            observed.value.value,
            NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value,
        ):
            raise ScientificContractError(ErrorMessage("fixed-score AUROC evidence does not match held-out evaluation"))
    elif expected != observed:
        raise ScientificContractError(
            ErrorMessage("fixed-score AUROC unavailable outcome does not match held-out evaluation")
        )
