from math import isclose

import pytest

from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome
from datp_core.analysis.inference.wilcoxon import CorrelationCoefficient
from datp_core.analysis.mechanisms.absorption import (
    AbsorptionCornerEvidence,
    AbsorptionFourCornerEvidence,
    AbsorptionSeedObservation,
    decide_absorption_cohort,
    decide_model_absorption,
)
from datp_core.analysis.mechanisms.association import (
    AssociationIssue,
    AssociationObservation,
    heterogeneity_benefit_association,
)
from datp_core.analysis.mechanisms.clustering import (
    ClusterPartitionSummary,
    ClusterStabilityResult,
    cluster_stability,
    empty_cluster_evidence_record,
)
from datp_core.analysis.mechanisms.dispersion import (
    GroupDispersionObservation,
    grouped_dispersion,
)
from datp_core.analysis.mechanisms.divergence import (
    ClientScoreVector,
    DivergenceBlocker,
    blocked_jensen_shannon_divergence,
    jensen_shannon_divergence,
)
from datp_core.analysis.mechanisms.movement import (
    ThresholdOperatingPoint,
    threshold_movement,
)
from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    ClusterIndex,
    MetricValue,
    ModelCoefficientValue,
    PairedObservationCount,
    ProximalCoefficient,
    Ratio,
    Seed,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.metrics import ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF
from datp_core.protocols.training import MODEL_ABSORPTION_DECISION_PROTOCOL


def test_association_reports_all_observations_with_typed_statistics() -> None:
    observations = (
        AssociationObservation(
            seed=Seed(0),
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            regime_label="alpha_0.1",
            heterogeneity=MetricValue(0.1),
            benefit=MetricValue(0.01),
        ),
        AssociationObservation(
            seed=Seed(1),
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            regime_label="alpha_0.3",
            heterogeneity=MetricValue(0.3),
            benefit=MetricValue(0.04),
        ),
        AssociationObservation(
            seed=Seed(2),
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            regime_label="alpha_0.7",
            heterogeneity=MetricValue(0.7),
            benefit=MetricValue(0.09),
        ),
    )
    result = heterogeneity_benefit_association(observations)
    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.issue is AssociationIssue.INSUFFICIENT_EVIDENCE
    assert result.observation_count == PairedObservationCount(3)
    assert result.statistics is not None
    assert isinstance(result.statistics.spearman_rho, CorrelationCoefficient)
    assert result.statistics.evidentiary_sufficient is False
    assert len(result.statistics.leave_one_out_slopes) == 3


def test_grouped_dispersion_has_one_typed_result_per_group() -> None:
    result = grouped_dispersion(
        (
            GroupDispersionObservation(
                group_index=ClusterIndex(0),
                thresholds=(ThresholdValue(0.2), ThresholdValue(0.4)),
                false_positive_rates=(Ratio(0.1), Ratio(0.2)),
            ),
            GroupDispersionObservation(
                group_index=ClusterIndex(1),
                thresholds=(ThresholdValue(0.6),),
                false_positive_rates=(Ratio(0.05),),
            ),
        )
    )
    assert result.evidence_role is EvidenceRole.MECHANISM
    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.group_sizes == (
        PairedObservationCount(2),
        PairedObservationCount(1),
    )
    assert result.singleton_groups == (ClusterIndex(1),)
    assert result.across_group_threshold_spread is not None
    assert isclose(result.across_group_threshold_spread.value, 0.3)


def test_cluster_stability_validates_contingency_margins() -> None:
    client_a = _client("a")
    client_b = _client("b")
    with pytest.raises(ValueError, match="row totals"):
        ClusterStabilityResult(
            adjusted_rand_index=CorrelationCoefficient(1.0),
            compared_clients=(client_a, client_b),
            left_partition=ClusterPartitionSummary(
                group_sizes=(
                    PairedObservationCount(1),
                    PairedObservationCount(1),
                )
            ),
            right_partition=ClusterPartitionSummary(
                group_sizes=(
                    PairedObservationCount(1),
                    PairedObservationCount(1),
                )
            ),
            contingency=(
                (PairedObservationCount(0), PairedObservationCount(0)),
                (PairedObservationCount(1), PairedObservationCount(1)),
            ),
        )


def test_partition_summary_preserves_unsorted_memberships_and_missing_middle_indexes() -> None:
    from tests.unit.thresholding.helpers import COORDINATE

    from datp_core.core.identifiers import AvailabilityStatus
    from datp_core.core.numeric import Quantile, RowCount
    from datp_core.thresholds.contracts import LocalQuantile, ThresholdDiagnostic
    from datp_core.thresholds.policies.cluster import ClusterMembership

    client_a = _client("a")
    client_b = _client("b")

    def membership(client: ClientIdentity, cluster_index: int, threshold: float) -> ClusterMembership:
        quantile = LocalQuantile(
            client=client,
            coordinate=COORDINATE,
            quantile=Quantile(0.95),
            value=ThresholdValue(threshold),
            calibration_count=RowCount(10),
            diagnostic=ThresholdDiagnostic(
                quantile_interpolation=None,
                score_set_checksum=Checksum("a" * 64),
                calibration_manifest_checksum=Checksum("b" * 64),
                tie_count=RowCount(0),
                availability=AvailabilityStatus.AVAILABLE,
            ),
        )
        return ClusterMembership(
            cluster_index=ClusterIndex(cluster_index),
            members=(client,),
            contributing_local_quantiles=(quantile,),
            cluster_threshold=ThresholdValue(threshold),
        )

    memberships = (
        membership(client_b, 2, 2.0),
        membership(client_a, 0, 1.0),
    )
    summary = ClusterPartitionSummary.from_memberships(
        memberships,
        declared_group_count=3,
        observed_empty_cluster_indexes=(ClusterIndex(1),),
    )
    assert summary.group_sizes == (
        PairedObservationCount(1),
        PairedObservationCount(0),
        PairedObservationCount(1),
    )
    assert summary.empty_cluster_indexes == (ClusterIndex(1),)

    stability = cluster_stability(
        memberships,
        memberships,
        left_declared_group_count=3,
        right_declared_group_count=3,
    )
    assert stability.compared_clients == (client_a, client_b)
    assert stability.left_partition.group_sizes == summary.group_sizes
    assert isclose(stability.adjusted_rand_index.value, 1.0)

    empty = empty_cluster_evidence_record(
        seed=Seed(0),
        source_threshold_checksum=Checksum("c" * 64),
        declared_group_count=3,
        filled_memberships=memberships,
        observed_empty_cluster_indexes=(ClusterIndex(1),),
        reason="declared empty cluster retained for negative evidence",
    )
    assert empty.partition.empty_cluster_indexes == (ClusterIndex(1),)
    assert empty.partition.group_sizes[1] == PairedObservationCount(0)


def test_threshold_movement_marks_attack_tradeoff_unavailable_without_attack_assignment() -> None:
    coordinate = FederatedTrainingCoordinate(
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    result = threshold_movement(
        client=_client("sensor_a", PopulationId.EDGE_SENSOR_GROUPS),
        shared=ThresholdOperatingPoint(
            threshold=ThresholdValue(0.4),
            fpr=Ratio(0.2),
            tpr=None,
        ),
        local=ThresholdOperatingPoint(
            threshold=ThresholdValue(0.6),
            fpr=Ratio(0.1),
            tpr=None,
        ),
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        coordinate=coordinate,
    )
    assert isclose(result.delta_threshold.value, 0.2)
    assert isclose(result.delta_fpr.value, -0.1)
    assert result.attack_availability is AvailabilityStatus.UNAVAILABLE


def test_jensen_shannon_is_deterministic_and_available() -> None:
    clients = (_client("a"), _client("b"), _client("c"))
    vectors = (
        ClientScoreVector(client=clients[0], scores=(MetricValue(0.1), MetricValue(0.2), MetricValue(0.15))),
        ClientScoreVector(client=clients[1], scores=(MetricValue(0.8), MetricValue(0.9), MetricValue(0.85))),
        ClientScoreVector(client=clients[2], scores=(MetricValue(0.4), MetricValue(0.5), MetricValue(0.45))),
    )
    first = jensen_shannon_divergence(vectors, source_score_checksum=Checksum("c" * 64))
    second = jensen_shannon_divergence(vectors, source_score_checksum=Checksum("c" * 64))
    assert first == second
    assert first.availability is AvailabilityStatus.AVAILABLE
    assert first.aggregate is not None
    assert len(first.pairwise_values) == 3


def test_unresolved_jsd_and_absorption_remain_typed() -> None:
    clients = (_client("a"), _client("b"))
    divergence = blocked_jensen_shannon_divergence(
        clients,
        DivergenceBlocker.BINNING_UNRESOLVED,
    )
    absorption = decide_model_absorption(MetricValue(0.0), MetricValue(0.2), MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert divergence.availability is AvailabilityStatus.UNAVAILABLE
    assert absorption.decision is ScientificDecision.BLOCKED


def test_model_absorption_follows_the_declared_retention_protocol() -> None:
    retained = decide_model_absorption(MetricValue(1.0), MetricValue(0.8), MODEL_ABSORPTION_DECISION_PROTOCOL)
    partial = decide_model_absorption(MetricValue(1.0), MetricValue(0.5), MODEL_ABSORPTION_DECISION_PROTOCOL)
    absorbed = decide_model_absorption(MetricValue(1.0), MetricValue(0.1), MODEL_ABSORPTION_DECISION_PROTOCOL)
    opposite = decide_model_absorption(MetricValue(1.0), MetricValue(-0.2), MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert retained.decision is ScientificDecision.SUPPORTED
    assert partial.decision is ScientificDecision.PARTIAL_ABSORPTION
    assert absorbed.decision is ScientificDecision.FULL_ABSORPTION
    assert opposite.decision is ScientificDecision.OPPOSITE_DIRECTION


def _absorption_observation(
    seed: int,
    *,
    reference_effect: float,
    personalized_effect: float,
    model_coefficient: ProximalCoefficient | ModelCoefficientValue | None = None,
    experiment: ExperimentId = ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
    personalized_model: TrainingModelId = TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
) -> AbsorptionSeedObservation:
    return AbsorptionSeedObservation(
        seed=Seed(seed),
        experiment=experiment,
        reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
        personalized_model=personalized_model,
        reference_effect=MetricValue(reference_effect),
        personalized_effect=MetricValue(personalized_effect),
        reference_shared_cv=MetricValue(0.5),
        reference_local_cv=MetricValue(0.5 - reference_effect),
        personalized_shared_cv=MetricValue(0.5),
        personalized_local_cv=MetricValue(0.5 - personalized_effect),
        model_coefficient=model_coefficient,
    )


def _checksum(tag: str) -> Checksum:
    return Checksum((tag.encode().hex() + "0" * 64)[:64])


def _corner(
    *,
    seed: int,
    model: TrainingModelId,
    method: FederatedThresholdMethod,
    cv: float,
    tag: str,
    coefficient: ModelCoefficientValue | None = None,
    experiment: ExperimentId = ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
) -> AbsorptionCornerEvidence:
    return AbsorptionCornerEvidence(
        seed=Seed(seed),
        experiment=experiment,
        population=PopulationId.NBAIOT_NATURAL_DEVICES.value,
        model=model,
        threshold_method=method,
        coefficient=coefficient,
        checkpoint_checksum=_checksum(f"{tag}-ckpt"),
        preprocessing_checksum=_checksum(f"{tag}-prep"),
        split_checksum=_checksum(f"{tag}-split"),
        calibration_score_checksum=_checksum(f"{tag}-cal"),
        evaluation_score_checksum=_checksum(f"{tag}-eval-score"),
        evaluation_checksum=_checksum(f"{tag}-eval"),
        client_inventory_checksum=_checksum(f"{tag}-clients"),
        eligibility_checksum=_checksum(f"{tag}-elig"),
        population_cv_fpr=MetricValue(cv),
    )


def test_absorption_cohort_requires_complete_seed_set_and_preserves_opposite_direction() -> None:
    incomplete = (_absorption_observation(0, reference_effect=0.2, personalized_effect=0.18),)
    assert decide_absorption_cohort(incomplete, MODEL_ABSORPTION_DECISION_PROTOCOL).decision.decision is (
        ScientificDecision.BLOCKED
    )
    opposite = tuple(
        _absorption_observation(
            seed,
            reference_effect=0.2,
            personalized_effect=-0.05 if seed % 2 == 0 else 0.18,
        )
        for seed in range(10)
    )
    result = decide_absorption_cohort(opposite, MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert result.decision.decision is ScientificDecision.OPPOSITE_DIRECTION
    assert result.retention_interval is not None


def test_absorption_ratio_unavailable_below_materiality_cutoff() -> None:
    cutoff = ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF.value
    near_zero = AbsorptionSeedObservation(
        seed=Seed(0),
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
        personalized_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        reference_effect=MetricValue(cutoff / 2.0),
        personalized_effect=MetricValue(cutoff / 4.0),
        reference_shared_cv=MetricValue(0.2),
        reference_local_cv=MetricValue(0.2 - cutoff / 2.0),
        personalized_shared_cv=MetricValue(0.2),
        personalized_local_cv=MetricValue(0.2 - cutoff / 4.0),
        ratio_unavailable_reason=(
            f"reference CV(FPR) effect is below the declared absorption denominator materiality cutoff ({cutoff})"
        ),
    )
    assert near_zero.retention_ratio is None
    cohort = tuple(
        AbsorptionSeedObservation(
            seed=Seed(seed),
            experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
            personalized_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
            reference_effect=MetricValue(cutoff / 2.0),
            personalized_effect=MetricValue(cutoff / 4.0),
            reference_shared_cv=MetricValue(0.2),
            reference_local_cv=MetricValue(0.2 - cutoff / 2.0),
            personalized_shared_cv=MetricValue(0.2),
            personalized_local_cv=MetricValue(0.2 - cutoff / 4.0),
            ratio_unavailable_reason=(
                f"reference CV(FPR) effect is below the declared absorption denominator materiality cutoff ({cutoff})"
            ),
        )
        for seed in range(CONFIRMATORY_SEED_COHORT.member_count.value)
    )
    result = decide_absorption_cohort(cohort, MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert result.decision.decision is ScientificDecision.INFEASIBLE
    assert "materiality cutoff" in result.decision.rationale


def test_absorption_from_corners_marks_near_zero_denominator_unavailable() -> None:
    seed = 0
    coefficient = ModelCoefficientValue(0.01)
    corners = AbsorptionFourCornerEvidence(
        seed=Seed(seed),
        experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
        personalized_model=TrainingModelId.FEDPROX_AUTOENCODER,
        reference_shared=_corner(
            seed=seed,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            cv=0.105,
            tag="ref-shared",
        ),
        reference_local=_corner(
            seed=seed,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            cv=0.1,
            tag="ref-local",
        ),
        personalized_shared=_corner(
            seed=seed,
            model=TrainingModelId.FEDPROX_AUTOENCODER,
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            cv=0.104,
            tag="pers-shared",
            coefficient=coefficient,
        ),
        personalized_local=_corner(
            seed=seed,
            model=TrainingModelId.FEDPROX_AUTOENCODER,
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            cv=0.101,
            tag="pers-local",
            coefficient=coefficient,
        ),
    )
    observation = AbsorptionSeedObservation.from_corners(corners)
    assert observation.reference_effect.value < ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF.value
    assert observation.retention_ratio is None
    assert observation.ratio_unavailable_reason is not None
    assert "materiality cutoff" in observation.ratio_unavailable_reason
    assert observation.corners is corners
    assert observation.model_coefficient == coefficient


def test_absorption_corners_reject_cloned_artifact_identities() -> None:
    seed = 0
    shared = _corner(
        seed=seed,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        cv=0.4,
        tag="same",
    )
    local = _corner(
        seed=seed,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        cv=0.2,
        tag="same",
    )
    personalized_shared = _corner(
        seed=seed,
        model=TrainingModelId.FEDPROX_AUTOENCODER,
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        cv=0.35,
        tag="pers-shared",
        coefficient=ModelCoefficientValue(0.1),
    )
    personalized_local = _corner(
        seed=seed,
        model=TrainingModelId.FEDPROX_AUTOENCODER,
        method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        cv=0.25,
        tag="pers-local",
        coefficient=ModelCoefficientValue(0.1),
    )
    with pytest.raises(ValueError, match="must not clone identical artifact identities"):
        AbsorptionFourCornerEvidence(
            seed=Seed(seed),
            experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
            personalized_model=TrainingModelId.FEDPROX_AUTOENCODER,
            reference_shared=shared,
            reference_local=local,
            personalized_shared=personalized_shared,
            personalized_local=personalized_local,
        )


def test_absorption_cohort_requires_unique_coefficient_when_declared() -> None:
    mixed = tuple(
        _absorption_observation(
            seed,
            reference_effect=0.2,
            personalized_effect=0.18,
            model_coefficient=ProximalCoefficient(0.01 if seed < 5 else 0.1),
            experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            personalized_model=TrainingModelId.FEDPROX_AUTOENCODER,
        )
        for seed in range(CONFIRMATORY_SEED_COHORT.member_count.value)
    )
    result = decide_absorption_cohort(mixed, MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert result.decision.decision is ScientificDecision.BLOCKED
    assert "one model coefficient" in result.decision.rationale


def test_absorption_cohort_uncertainty_rules_require_available_bca_bounds() -> None:
    retained = tuple(
        _absorption_observation(
            seed,
            reference_effect=0.2 + 0.01 * (seed % 3),
            personalized_effect=0.19 + 0.005 * (seed % 3),
        )
        for seed in range(CONFIRMATORY_SEED_COHORT.member_count.value)
    )
    retained_result = decide_absorption_cohort(retained, MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert retained_result.retention_interval is not None
    assert retained_result.retention_interval.outcome is BcaOutcome.AVAILABLE
    assert retained_result.decision.decision is ScientificDecision.SUPPORTED

    absorbed = tuple(
        _absorption_observation(
            seed,
            reference_effect=0.3 + 0.01 * (seed % 3),
            personalized_effect=0.02 + 0.005 * (seed % 3),
        )
        for seed in range(CONFIRMATORY_SEED_COHORT.member_count.value)
    )
    absorbed_result = decide_absorption_cohort(absorbed, MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert absorbed_result.retention_interval is not None
    assert absorbed_result.retention_interval.outcome is BcaOutcome.AVAILABLE
    assert absorbed_result.decision.decision is ScientificDecision.FULL_ABSORPTION

    straddling = tuple(
        _absorption_observation(
            seed,
            reference_effect=0.2,
            personalized_effect=0.18 if seed < 5 else 0.02,
        )
        for seed in range(CONFIRMATORY_SEED_COHORT.member_count.value)
    )
    straddle_result = decide_absorption_cohort(straddling, MODEL_ABSORPTION_DECISION_PROTOCOL)
    assert straddle_result.decision.decision is ScientificDecision.DIRECTIONAL_INCONCLUSIVE
    assert "straddle" in straddle_result.decision.rationale


def _client(
    client_id: str,
    population: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES,
) -> ClientIdentity:
    kind = (
        PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS
        if population is PopulationId.EDGE_SENSOR_GROUPS
        else PopulationIdentityKind.PHYSICAL_DEVICES
    )
    return ClientIdentity(population, client_id, kind)
