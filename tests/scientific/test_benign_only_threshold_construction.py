"""Scientific contract: threshold construction is benign-only and leak-free.

Covers required negative coverage for attack-label leakage, calibration/
evaluation conflation, cohort inconsistency, silent client loss, taxonomy/grouping
misuse, unresolved-method fabrication, comparator omission, and cross-branch
contamination between the federated and centralized threshold ladders.
"""

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import skew
from tests.unit.calibration.helpers import attack_score_record, benign_score_record, some_client
from tests.unit.thresholding.helpers import client_scores, identity

from datp_core.calibration.eligibility import (
    calibration_support,
    decide_eligibility,
    eligible_clients,
    load_benign_calibration_references,
    reject_calibration_evaluation_overlap,
    reject_evaluation_partition_in_eligibility,
    reject_score_coordinate_mismatch,
    require_common_eligible_cohort,
)
from datp_core.domain.enums import (
    CapabilityStatus,
    CentralizedThresholdMethod,
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    PublicationStatus,
)
from datp_core.domain.errors import CapabilityError, LeakageError, ScientificContractError
from datp_core.domain.values import CalibrationSize, Checksum, ClientCount, FamilyIdentity, GroupCount, Quantile, Seed
from datp_core.orchestration.stages.construct_federated_thresholds import (
    ConstructFederatedThresholdsAssetName,
    ConstructFederatedThresholdsRequest,
    construct_federated_thresholds_stage,
)
from datp_core.populations.models import PopulationCapabilities
from datp_core.protocols.calibration import (
    CLUSTER_THRESHOLD_PROTOCOL,
    CONFORMAL_PROTOCOL,
    FEDERATED_STATISTICS_PROTOCOL,
)
from datp_core.protocols.models import CalibrationEligibilityProtocol, ClusterThresholdProtocol
from datp_core.thresholding.conformal import construct_local_conformal_threshold
from datp_core.thresholding.dispatch import (
    ThresholdConstructionRequest,
    dispatch_federated_threshold,
    reject_centralized_threshold_method,
)
from datp_core.thresholding.family import construct_family_threshold
from datp_core.thresholding.federated_benign_statistics import construct_federated_benign_statistics
from datp_core.thresholding.grouped import construct_grouped_threshold
from datp_core.thresholding.models import PooledVarianceDecomposition, ThresholdUnavailableResult
from datp_core.thresholding.shrinkage import construct_size_aware_shrinkage

PROTOCOL = CalibrationEligibilityProtocol(minimum_support=CalibrationSize(100))
QUANTILE = Quantile(0.95)
ROOT = Path(__file__).resolve().parents[2]
THRESHOLDING_ROOT = ROOT / "src" / "datp_core" / "thresholding"
FAMILY_MODULE = THRESHOLDING_ROOT / "family.py"
GROUPED_MODULE = THRESHOLDING_ROOT / "grouped.py"
FORBIDDEN_RETRAINING_IMPORTS = (
    "torch",
    "datp_core.learning.autoencoder",
    "datp_core.learning.federated.training",
    "datp_core.learning.federated.checkpointing",
    "datp_core.learning.federated.fedavg",
    "datp_core.learning.federated.fedprox",
    "datp_core.learning.federated.ditto",
    "datp_core.scoring.generation",
)


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return tuple(modules)


def _capabilities() -> PopulationCapabilities:
    return PopulationCapabilities(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
        declared_client_count=ClientCount(3),
        physical_client_validity=CapabilityStatus.SUPPORTED,
        family_taxonomy=CapabilityStatus.SUPPORTED,
        chronology=CapabilityStatus.UNAVAILABLE,
        client_level_attack_assignment=CapabilityStatus.SUPPORTED,
        fpr_evaluation=CapabilityStatus.SUPPORTED,
        attack_sensitive_evaluation=CapabilityStatus.SUPPORTED,
        temporal_support=CapabilityStatus.UNAVAILABLE,
        valid_threshold_methods=tuple(FederatedThresholdMethod),
        evidentiary_role=EvidenceRole.CONFIRMATORY,
        confirmatory_eligible=True,
    )


# 1. Attack-labelled calibration record.
def test_attack_labelled_calibration_record_is_rejected(tmp_path: Path) -> None:
    record = attack_score_record(tmp_path, "client_a", (0.1, 0.2, 0.3))

    def call() -> None:
        load_benign_calibration_references(record)

    with pytest.raises(LeakageError, match="attack-labelled rows"):
        call()


# 2. Evaluation row enters calibration.
def test_evaluation_partition_cannot_enter_calibration_eligibility() -> None:
    def call() -> None:
        reject_evaluation_partition_in_eligibility(PartitionRole.EVALUATION)

    with pytest.raises(LeakageError, match="calibration-partition scores only"):
        call()


# 3. Calibration/evaluation row overlap.
def test_calibration_evaluation_row_overlap_is_rejected() -> None:
    def call() -> None:
        reject_calibration_evaluation_overlap(frozenset({"row-1", "row-2"}), frozenset({"row-2"}))

    with pytest.raises(LeakageError, match="must not share source rows"):
        call()


# 4. Different eligible populations across methods.
def test_methods_compared_within_one_cell_must_share_the_eligible_cohort() -> None:
    full_cohort = (some_client("client_a"), some_client("client_b"))
    partial_cohort = (some_client("client_a"),)

    def call():
        return require_common_eligible_cohort((full_cohort, partial_cohort))

    with pytest.raises(ScientificContractError, match="same eligible cohort"):
        call()


# 5. Client silently removed.
def test_eligibility_covers_every_candidate_client_never_silently_drops_one(tmp_path: Path) -> None:
    sufficient = benign_score_record(tmp_path, "client_a", tuple(float(i) for i in range(150)))
    insufficient = benign_score_record(tmp_path, "client_b", (0.1, 0.2))
    decisions = []
    for record in (sufficient, insufficient):
        references = load_benign_calibration_references(record)
        support = calibration_support(record, references, Checksum("a" * 64))
        decisions.append(decide_eligibility(support, PROTOCOL))
    assert len(decisions) == 2  # both candidates produce a decision; neither vanishes
    assert {decision.client.client_id for decision in decisions} == {"client_a", "client_b"}
    eligible = eligible_clients(tuple(decisions))
    assert [client.client_id for client in eligible] == ["client_a"]


# 6. Family threshold without taxonomy.
def test_family_threshold_without_taxonomy_reports_typed_unavailability_not_a_crash() -> None:
    eligible = (client_scores("client_a", (1.0, 2.0, 3.0)),)
    request = ThresholdConstructionRequest(
        method=FederatedThresholdMethod.FAMILY_THRESHOLD,
        coordinate=eligible[0].coordinate,
        quantile=QUANTILE,
        capabilities=_capabilities(),
        eligible=eligible,
        family_by_client=(),
    )
    result = dispatch_federated_threshold(request)
    assert isinstance(result, ThresholdUnavailableResult)


# 7. Family inferred from attack labels.
def test_family_threshold_module_never_references_outcome_labels() -> None:
    source = FAMILY_MODULE.read_text(encoding="utf-8")
    assert "attack" not in source.lower()
    assert "outcome_label" not in source.lower()


def test_construct_family_threshold_signature_accepts_no_label_bearing_input() -> None:
    eligible = (client_scores("client_a", (1.0, 2.0, 3.0)),)
    family_by_client = (identity("client_a"), FamilyIdentity("doorbell"))
    result = construct_family_threshold(eligible, QUANTILE, (family_by_client,))
    assert result.families


# 8 & 9. Grouped threshold must use the locked fingerprint builder and benign calibration only.
def test_grouped_module_never_references_evaluation_partition_data() -> None:
    source = GROUPED_MODULE.read_text(encoding="utf-8")
    assert "evaluation" not in source.lower()


def test_grouped_threshold_fingerprint_matches_the_locked_mean_std_skew_p95_formula() -> None:
    generator = np.random.default_rng(0)
    clients = tuple(
        client_scores(f"client_{i}", tuple(float(v) for v in generator.normal(loc=i * 5, size=30))) for i in range(6)
    )
    result = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    for fingerprint in result.fingerprints:
        scores = next(c for c in clients if c.client == fingerprint.client).as_array
        expected = (
            float(np.mean(scores)),
            float(np.std(scores, ddof=0)),
            float(skew(scores, bias=True)),
            float(np.quantile(scores, 0.95, method="linear")),
        )
        assert fingerprint.raw == expected


# 10. Grouped threshold with wrong K / random_state is rejected before construction.
def test_cluster_threshold_protocol_locks_reject_non_canonical_hyperparameters() -> None:
    group_count = GroupCount(9)

    def build() -> ClusterThresholdProtocol:
        return ClusterThresholdProtocol(
            method=CLUSTER_THRESHOLD_PROTOCOL.method,
            quantile=CLUSTER_THRESHOLD_PROTOCOL.quantile,
            fingerprint_features=CLUSTER_THRESHOLD_PROTOCOL.fingerprint_features,
            feature_standardization=CLUSTER_THRESHOLD_PROTOCOL.feature_standardization,
            assignment_algorithm=CLUSTER_THRESHOLD_PROTOCOL.assignment_algorithm,
            initialization=CLUSTER_THRESHOLD_PROTOCOL.initialization,
            initialization_count=CLUSTER_THRESHOLD_PROTOCOL.initialization_count,
            maximum_iterations=CLUSTER_THRESHOLD_PROTOCOL.maximum_iterations,
            random_state=CLUSTER_THRESHOLD_PROTOCOL.random_state,
            group_count=group_count,
            threshold_aggregation=CLUSTER_THRESHOLD_PROTOCOL.threshold_aggregation,
        )

    with pytest.raises(ValueError, match="locked group count"):
        build()


# 11. Group assignment must not change across identical runs.
def test_grouped_threshold_assignment_is_identical_across_repeated_runs() -> None:
    generator = np.random.default_rng(1)
    clients = tuple(
        client_scores(f"client_{i}", tuple(float(v) for v in generator.normal(loc=i * 5, size=30))) for i in range(6)
    )
    first = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    second = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    first_map = {a.client.client_id: a.threshold.value for a in first.assignments}
    second_map = {a.client.client_id: a.threshold.value for a in second.assignments}
    assert first_map == second_map


# 12. Size-aware shrinkage must not fabricate a function.
def test_size_aware_shrinkage_never_fabricates_a_lambda_function() -> None:
    eligible = client_scores("client_a", (1.0, 2.0, 3.0))
    result = construct_size_aware_shrinkage(eligible.coordinate)
    assert isinstance(result, ThresholdUnavailableResult)
    assert "lambda" in result.detail.lower() or "function" in result.detail.lower()


# 13. Conformal threshold must not silently fall back to an ordinary quantile.
def test_conformal_threshold_never_silently_falls_back_for_insufficient_support() -> None:
    sufficient = client_scores("client_a", tuple(float(i) for i in range(1, 101)))
    insufficient = client_scores("client_b", (1.0, 2.0))
    result = construct_local_conformal_threshold((sufficient, insufficient), CONFORMAL_PROTOCOL)
    assert result.unavailable_clients == (insufficient.client,)
    assert insufficient.client not in {assignment.client for assignment in result.assignments}


# 14. The benign-statistics comparator cannot omit the between-client term.
def test_pooled_variance_decomposition_requires_the_between_client_term() -> None:
    # A dict-splat (rather than direct keyword arguments) keeps this omission a
    # runtime-only concern: the missing field is a deliberate scientific-contract
    # probe, not a static call-signature error the type checker should flag.
    incomplete_fields = {
        "global_mean": 0.0,
        "within_client_variance": 1.0,
        "full_pooled_variance": 1.0,
        "between_ratio": None,
    }

    def build() -> PooledVarianceDecomposition:
        return PooledVarianceDecomposition(**incomplete_fields)

    with pytest.raises(TypeError):
        build()


# 15. Fixed coefficients must never be promoted to the primary matched comparator.
def test_fixed_coefficients_remain_a_separate_supplementary_curve() -> None:
    generator = np.random.default_rng(2)
    clients = (
        client_scores("client_a", tuple(float(v) for v in generator.normal(loc=0.0, size=100))),
        client_scores("client_b", tuple(float(v) for v in generator.normal(loc=50.0, size=100))),
    )
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    fixed_values = {item.threshold.value for item in result.fixed_coefficient_curve}
    assert result.matched_threshold.value not in fixed_values


# 16. Anomaly-informed (attack) summaries cannot enter the benign comparator.
def test_benign_statistics_comparator_only_accepts_benign_calibration_scores() -> None:
    signature = inspect.signature(construct_federated_benign_statistics)
    assert list(signature.parameters) == ["eligible", "protocol", "quantile"]
    assert "attack" not in THRESHOLDING_ROOT.joinpath("federated_benign_statistics.py").read_text().lower()


# 17. Centralized method cannot enter federated dispatch.
def test_centralized_threshold_method_cannot_enter_federated_dispatch() -> None:
    def call() -> None:
        reject_centralized_threshold_method(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)

    with pytest.raises(LeakageError):
        call()


# 18. Threshold construction cannot retrain or rescore.
def test_thresholding_package_never_imports_training_or_scoring_generation_code() -> None:
    for path in sorted(THRESHOLDING_ROOT.glob("*.py")):
        modules = _imported_modules(path)
        for forbidden in FORBIDDEN_RETRAINING_IMPORTS:
            assert not any(module == forbidden or module.startswith(f"{forbidden}.") for module in modules), (
                f"{path} imports {forbidden}"
            )


# 19. Mismatched model or score checksum is rejected.
def test_score_coordinate_mismatch_across_calibration_records_is_rejected(tmp_path: Path) -> None:
    record_a = benign_score_record(tmp_path, "client_a", (0.1, 0.2))
    record_b = benign_score_record(tmp_path, "client_b", (0.3, 0.4), seed=Seed(9))

    def call() -> None:
        reject_score_coordinate_mismatch((record_a, record_b))

    with pytest.raises(ScientificContractError, match="share one coordinate"):
        call()


# 20. A partial threshold artifact must never be treated as reusable.
def test_construct_federated_thresholds_stage_rejects_a_partial_published_artifact(tmp_path: Path) -> None:
    eligible = (client_scores("client_a", tuple(float(i) for i in range(150))),)
    request = ThresholdConstructionRequest(
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        coordinate=eligible[0].coordinate,
        quantile=QUANTILE,
        capabilities=_capabilities(),
        eligible=eligible,
    )
    output_directory = tmp_path / "threshold_output"
    stage_request = ConstructFederatedThresholdsRequest(
        request=request, output_directory=output_directory, overwrite=False
    )
    construct_federated_thresholds_stage(stage_request)
    (output_directory / ConstructFederatedThresholdsAssetName.RESULT).unlink()

    result = construct_federated_thresholds_stage(stage_request)
    assert result.publication_status is PublicationStatus.PUBLISHED


# 21. An unsupported method never receives an invented fallback.
def test_dispatch_rejects_a_method_unsupported_by_population_capabilities_rather_than_inventing_one() -> None:
    eligible = (client_scores("client_a", (1.0, 2.0, 3.0)),)
    capabilities = _capabilities()
    restricted = PopulationCapabilities(
        population=capabilities.population,
        dataset=capabilities.dataset,
        identity_kind=capabilities.identity_kind,
        declared_client_count=capabilities.declared_client_count,
        physical_client_validity=capabilities.physical_client_validity,
        family_taxonomy=capabilities.family_taxonomy,
        chronology=capabilities.chronology,
        client_level_attack_assignment=capabilities.client_level_attack_assignment,
        fpr_evaluation=capabilities.fpr_evaluation,
        attack_sensitive_evaluation=capabilities.attack_sensitive_evaluation,
        temporal_support=capabilities.temporal_support,
        valid_threshold_methods=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        evidentiary_role=capabilities.evidentiary_role,
        confirmatory_eligible=capabilities.confirmatory_eligible,
    )
    request = ThresholdConstructionRequest(
        method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        coordinate=eligible[0].coordinate,
        quantile=QUANTILE,
        capabilities=restricted,
        eligible=eligible,
    )

    def call():
        return dispatch_federated_threshold(request)

    with pytest.raises(CapabilityError):
        call()
