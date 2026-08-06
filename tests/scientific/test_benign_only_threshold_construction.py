"""Scientific contract: threshold construction is benign-only and leak-free."""

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
from datp_core.datasets.capabilities import CapabilityStatus
from datp_core.datasets.partitioning.contracts import PopulationCapabilities
from datp_core.domain.enums import (
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
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import CalibrationSize, ClientCount, GroupCount, Seed
from datp_core.domain.values.paths import FamilyIdentity
from datp_core.domain.values.ratios import Quantile
from datp_core.pipeline.decision.federated import (
    ConstructFederatedThresholdsRequest,
    construct_federated_thresholds,
)
from datp_core.protocols.calibration import (
    CLUSTER_THRESHOLD_PROTOCOL,
    FEDERATED_STATISTICS_PROTOCOL,
    CalibrationEligibilityProtocol,
    ClusterThresholdProtocol,
)
from datp_core.thresholding.dispatch import (
    ThresholdConstructionRequest,
    dispatch_federated_threshold,
    reject_centralized_threshold_method,
)
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.methods.cluster import construct_grouped_threshold
from datp_core.thresholding.methods.conformal import construct_local_conformal_threshold
from datp_core.thresholding.methods.family import construct_family_threshold
from datp_core.thresholding.methods.federated_statistics import (
    PooledVarianceDecomposition,
    construct_federated_benign_statistics,
)
from datp_core.thresholding.methods.shrinkage import construct_size_aware_shrinkage
from datp_core.thresholding.publication import FederatedThresholdAssetName

PROTOCOL = CalibrationEligibilityProtocol(minimum_support=CalibrationSize(100))
QUANTILE = Quantile(0.95)
ROOT = Path(__file__).resolve().parents[2]
THRESHOLDING_ROOT = ROOT / "src" / "datp_core" / "thresholding"
METHODS_ROOT = THRESHOLDING_ROOT / "methods"
FAMILY_MODULE = METHODS_ROOT / "family.py"
CLUSTER_MODULE = METHODS_ROOT / "cluster.py"
FEDERATED_STATISTICS_MODULE = METHODS_ROOT / "federated_statistics.py"
FORBIDDEN_RETRAINING_IMPORTS = (
    "torch",
    "datp_core.learning.autoencoder",
    "datp_core.learning.federated.training",
    "datp_core.learning.federated.checkpoints",
    "datp_core.learning.federated.fedavg",
    "datp_core.learning.federated.fedprox",
    "datp_core.learning.federated.ditto",
    "datp_core.pipeline.scoring.frames",
    "datp_core.pipeline.scoring.federated",
    "datp_core.pipeline.scoring.centralized",
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


def test_attack_labelled_calibration_record_is_rejected(tmp_path: Path) -> None:
    record = attack_score_record(tmp_path, "client_a", (0.1, 0.2, 0.3))
    with pytest.raises(LeakageError, match="attack-labelled rows"):
        load_benign_calibration_references(record)


def test_evaluation_partition_cannot_enter_calibration_eligibility() -> None:
    with pytest.raises(LeakageError, match="calibration-partition scores only"):
        reject_evaluation_partition_in_eligibility(PartitionRole.EVALUATION)


def test_calibration_evaluation_row_overlap_is_rejected() -> None:
    with pytest.raises(LeakageError, match="must not share source rows"):
        reject_calibration_evaluation_overlap(frozenset({"row-1", "row-2"}), frozenset({"row-2"}))


def test_methods_compared_within_one_cell_must_share_the_eligible_cohort() -> None:
    with pytest.raises(ScientificContractError, match="same eligible cohort"):
        require_common_eligible_cohort(((some_client("client_a"), some_client("client_b")), (some_client("client_a"),)))


def test_eligibility_covers_every_candidate_client_never_silently_drops_one(tmp_path: Path) -> None:
    records = (
        benign_score_record(tmp_path, "client_a", tuple(float(index) for index in range(150))),
        benign_score_record(tmp_path, "client_b", (0.1, 0.2)),
    )
    decisions = tuple(
        decide_eligibility(
            calibration_support(
                record,
                load_benign_calibration_references(record),
                Checksum("a" * 64),
            ),
            PROTOCOL,
        )
        for record in records
    )
    assert len(decisions) == 2
    assert frozenset(item.client.client_id for item in decisions) == frozenset({"client_a", "client_b"})
    assert tuple(client.client_id for client in eligible_clients(decisions)) == ("client_a",)


def test_family_threshold_without_taxonomy_reports_typed_unavailability_not_a_crash() -> None:
    eligible = (client_scores("client_a", (1.0, 2.0, 3.0)),)
    result = dispatch_federated_threshold(
        ThresholdConstructionRequest(
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
            coordinate=eligible[0].coordinate,
            quantile=QUANTILE,
            capabilities=_capabilities(),
            eligible=eligible,
            family_by_client=(),
        )
    )
    assert isinstance(result, ThresholdUnavailableResult)


def test_family_threshold_module_never_references_outcome_labels() -> None:
    source = FAMILY_MODULE.read_text(encoding="utf-8").lower()
    assert "attack" not in source
    assert "outcome_label" not in source


def test_construct_family_threshold_signature_accepts_no_label_bearing_input() -> None:
    result = construct_family_threshold(
        (client_scores("client_a", (1.0, 2.0, 3.0)),),
        QUANTILE,
        ((identity("client_a"), FamilyIdentity("doorbell")),),
    )
    assert result.families


def test_cluster_module_never_references_evaluation_partition_data() -> None:
    assert "evaluation" not in CLUSTER_MODULE.read_text(encoding="utf-8").lower()


def test_grouped_threshold_fingerprint_matches_locked_formula() -> None:
    generator = np.random.default_rng(0)
    clients = tuple(
        client_scores(
            f"client_{index}",
            tuple(float(value) for value in generator.normal(loc=index * 5, size=30)),
        )
        for index in range(6)
    )
    result = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    for fingerprint in result.fingerprints:
        scores = next(item.as_array for item in clients if item.client == fingerprint.client)
        assert fingerprint.raw == (
            float(np.mean(scores)),
            float(np.std(scores, ddof=0)),
            float(skew(scores, bias=True)),
            float(np.quantile(scores, 0.95, method="linear")),
        )


def test_cluster_threshold_protocol_locks_reject_non_canonical_hyperparameters() -> None:
    with pytest.raises(ValueError, match="locked group count"):
        ClusterThresholdProtocol(
            method=CLUSTER_THRESHOLD_PROTOCOL.method,
            quantile=CLUSTER_THRESHOLD_PROTOCOL.quantile,
            fingerprint_features=CLUSTER_THRESHOLD_PROTOCOL.fingerprint_features,
            feature_standardization=CLUSTER_THRESHOLD_PROTOCOL.feature_standardization,
            assignment_algorithm=CLUSTER_THRESHOLD_PROTOCOL.assignment_algorithm,
            initialization=CLUSTER_THRESHOLD_PROTOCOL.initialization,
            initialization_count=CLUSTER_THRESHOLD_PROTOCOL.initialization_count,
            maximum_iterations=CLUSTER_THRESHOLD_PROTOCOL.maximum_iterations,
            random_state=CLUSTER_THRESHOLD_PROTOCOL.random_state,
            group_count=GroupCount(9),
            threshold_aggregation=CLUSTER_THRESHOLD_PROTOCOL.threshold_aggregation,
        )


def test_grouped_threshold_assignment_is_identical_across_repeated_runs() -> None:
    generator = np.random.default_rng(1)
    clients = tuple(
        client_scores(
            f"client_{index}",
            tuple(float(value) for value in generator.normal(loc=index * 5, size=30)),
        )
        for index in range(6)
    )
    first = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    second = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    assert tuple((item.client.client_id, item.threshold.value) for item in first.assignments) == tuple(
        (item.client.client_id, item.threshold.value) for item in second.assignments
    )


def test_size_aware_shrinkage_never_fabricates_a_lambda_function() -> None:
    result = construct_size_aware_shrinkage(client_scores("client_a", (1.0, 2.0, 3.0)).coordinate)
    assert isinstance(result, ThresholdUnavailableResult)
    assert "lambda" in result.detail.lower() or "function" in result.detail.lower()


def test_conformal_threshold_never_silently_falls_back_for_insufficient_support() -> None:
    sufficient = client_scores("client_a", tuple(float(index) for index in range(1, 101)))
    insufficient = client_scores("client_b", (1.0, 2.0))
    result = construct_local_conformal_threshold((sufficient, insufficient), QUANTILE)
    assert result.unavailable_clients == (insufficient.client,)
    assert insufficient.client not in frozenset(assignment.client for assignment in result.assignments)


def test_pooled_variance_decomposition_requires_between_client_term() -> None:
    with pytest.raises(TypeError):
        PooledVarianceDecomposition(  # type: ignore[call-arg]
            global_mean=0.0,
            within_client_variance=1.0,
            full_pooled_variance=1.0,
            between_ratio=None,
        )


def test_fixed_coefficients_remain_a_separate_supplementary_curve() -> None:
    generator = np.random.default_rng(2)
    clients = (
        client_scores("client_a", tuple(float(value) for value in generator.normal(size=100))),
        client_scores("client_b", tuple(float(value) for value in generator.normal(loc=50.0, size=100))),
    )
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    assert result.matched_threshold.value not in frozenset(
        item.threshold.value for item in result.fixed_coefficient_curve
    )


def test_benign_statistics_comparator_only_accepts_benign_calibration_scores() -> None:
    assert tuple(inspect.signature(construct_federated_benign_statistics).parameters) == (
        "eligible",
        "protocol",
        "quantile",
    )
    assert "attack" not in FEDERATED_STATISTICS_MODULE.read_text(encoding="utf-8").lower()


def test_centralized_threshold_method_cannot_enter_federated_dispatch() -> None:
    with pytest.raises(LeakageError):
        reject_centralized_threshold_method(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)


def test_thresholding_package_never_imports_training_or_scoring_generation_code() -> None:
    for path in sorted(THRESHOLDING_ROOT.rglob("*.py")):
        modules = _imported_modules(path)
        for forbidden in FORBIDDEN_RETRAINING_IMPORTS:
            assert not any(module == forbidden or module.startswith(f"{forbidden}.") for module in modules), (
                f"{path} imports {forbidden}"
            )


def test_score_coordinate_mismatch_across_calibration_records_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="share one coordinate"):
        reject_score_coordinate_mismatch(
            (
                benign_score_record(tmp_path, "client_a", (0.1, 0.2)),
                benign_score_record(tmp_path, "client_b", (0.3, 0.4), seed=Seed(9)),
            )
        )


def test_construct_federated_thresholds_rejects_partial_artifact(tmp_path: Path) -> None:
    eligible = (client_scores("client_a", tuple(float(index) for index in range(150))),)
    output_directory = tmp_path / "threshold_output"
    request = ConstructFederatedThresholdsRequest(
        request=ThresholdConstructionRequest(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            coordinate=eligible[0].coordinate,
            quantile=QUANTILE,
            capabilities=_capabilities(),
            eligible=eligible,
            family_by_client=(),
        ),
        output_directory=output_directory,
        overwrite=False,
    )
    construct_federated_thresholds(request)
    (output_directory / FederatedThresholdAssetName.RESULT).unlink()
    result = construct_federated_thresholds(request)
    assert result.publication_status is PublicationStatus.PUBLISHED


def test_dispatch_rejects_method_unsupported_by_population_capabilities() -> None:
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
    with pytest.raises(CapabilityError):
        dispatch_federated_threshold(
            ThresholdConstructionRequest(
                method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
                coordinate=eligible[0].coordinate,
                quantile=QUANTILE,
                capabilities=restricted,
                eligible=eligible,
                family_by_client=(),
            )
        )
