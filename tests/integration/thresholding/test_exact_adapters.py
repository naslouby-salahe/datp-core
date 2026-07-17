from dataclasses import dataclass
from decimal import Decimal

import pytest
from tests.support.score_artifacts import calibration_scores_for_clients

from datp_core.application.ports.thresholding import (
    AssignThresholdRequest,
    B4ClusteringRequest,
    QuantileEstimateRequest,
    ThresholdAssignmentMetadata,
)
from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity, ThresholdIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.splitting import (
    BenignCalibrationSplitSpec,
    ConformalQuantileIndexRule,
    ConformalSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import ThresholdError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.operating_points import (
    ClientEligibilityReason,
    EligibleClientSet,
    IneligibleClientReason,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import CalibrationScoreArtifactSet, QuantileEstimatorType
from datp_core.domain.runtime.seeds import Seed
from datp_core.domain.thresholding.clustering import (
    B4ClusteringAlgorithm,
    B4ClusteringSpec,
    B4FingerprintField,
    B4FingerprintFitScope,
    B4FingerprintScalerSpec,
    CanonicalB4ClusteringProfile,
    ClusterAssignmentArtifact,
    ClusterAssignmentEntry,
    ClusterCentroidReference,
    ClusterThresholdAggregationSpec,
    KMeansInitializationCount,
    KMeansMaximumIterations,
    PinnedScikitLearnVersion,
    ScaledB4Fingerprint,
    ScaledFingerprintReference,
    adjusted_rand_index,
)
from datp_core.domain.thresholding.federated_statistics import (
    FedStatsBenignThresholdSpec,
    ThresholdComparatorRole,
)
from datp_core.domain.thresholding.policies import (
    ClusterThresholdSpec,
    CoreThresholdPolicy,
    FamilyThresholdSpec,
    FprTarget,
    LocalThresholdSpec,
    SharedThresholdConstruction,
    SharedThresholdSpec,
    ThresholdAssignment,
    ThresholdConstructionKind,
    ThresholdConstructionSpec,
    ThresholdPercentile,
    ThresholdValue,
)
from datp_core.domain.thresholding.variants import (
    CalibrationSizeFallbackThresholdSpec,
    ConformalMode,
    ConformalThresholdSpec,
    RobustClusterMedianThresholdSpec,
    ShrinkageThresholdSpec,
    ShrinkageWeight,
    ThresholdVariant,
)
from datp_core.infrastructure.thresholding.clustering import ExactB4ClusteringStrategy
from datp_core.infrastructure.thresholding.federated_statistics import FedStatsThresholdStrategy
from datp_core.infrastructure.thresholding.policies import (
    ClusterThresholdStrategy,
    FamilyThresholdStrategy,
    LocalThresholdStrategy,
    SharedThresholdStrategy,
)
from datp_core.infrastructure.thresholding.quantiles import ExactQuantileEstimator
from datp_core.infrastructure.thresholding.variants import VariantThresholdStrategy


@dataclass(frozen=True, slots=True, kw_only=True)
class _SyntheticScoreReader:
    values: tuple[tuple[float, ...], ...]

    def read(self, *, calibration_scores: CalibrationScoreArtifactSet, client_index: int) -> tuple[float, ...]:
        del calibration_scores
        return self.values[client_index]


@pytest.mark.integration
def test_exact_quantile_estimators_return_their_locked_constructions() -> None:
    values = ((1.0, 2.0, 10.0), (3.0, 4.0, 5.0, 6.0))
    score_set, _ = calibration_scores_for_clients(values)
    request = QuantileEstimateRequest(calibration_scores=score_set, percentile=ThresholdPercentile(value=0.95))

    reader = _SyntheticScoreReader(values=values)
    local = ExactQuantileEstimator(estimator=QuantileEstimatorType.LOCAL_EXACT, reader=reader)
    pooled = ExactQuantileEstimator(estimator=QuantileEstimatorType.POOLED_EXACT, reader=reader)
    weighted = ExactQuantileEstimator(estimator=QuantileEstimatorType.WEIGHTED_EXACT, reader=reader)
    oracle = ExactQuantileEstimator(estimator=QuantileEstimatorType.CENTRALIZED_ORACLE, reader=reader)

    assert tuple(entry.value.value for entry in local.estimate(request).estimates.values.entries) == (10.0, 6.0)
    assert tuple(entry.value.value for entry in pooled.estimate(request).estimates.values.entries) == (10.0, 10.0)
    assert tuple(entry.value.value for entry in weighted.estimate(request).estimates.values.entries) == (10.0, 10.0)
    assert tuple(entry.value.value for entry in oracle.estimate(request).estimates.values.entries) == (10.0, 10.0)


def _canonical_b4_profile() -> CanonicalB4ClusteringProfile:
    return CanonicalB4ClusteringProfile(
        fingerprint_fields=(
            B4FingerprintField.MEAN,
            B4FingerprintField.STANDARD_DEVIATION,
            B4FingerprintField.SKEW,
            B4FingerprintField.P95,
        ),
        scaler=B4FingerprintScalerSpec.STANDARD_SCALER,
        scaler_fit_scope=B4FingerprintFitScope.ELIGIBLE_CLIENT_FINGERPRINTS,
        algorithm=B4ClusteringAlgorithm.KMEANS_PLUS_PLUS,
        n_init=KMeansInitializationCount(value=10),
        max_iter=KMeansMaximumIterations(value=300),
        scikit_learn_version=PinnedScikitLearnVersion(value="1.9.0"),
    )


@pytest.mark.integration
def test_exact_b4_clustering_is_repeatable_with_perfect_adjusted_rand() -> None:
    values = (
        (0.0, 0.1, 0.2, 0.3),
        (0.1, 0.2, 0.2, 0.4),
        (9.9, 10.0, 10.1, 10.2),
        (10.0, 10.1, 10.2, 10.3),
        (19.9, 20.0, 20.1, 20.2),
        (20.0, 20.1, 20.2, 20.3),
    )
    score_set, eligible_clients = calibration_scores_for_clients(values)
    specification = B4ClusteringSpec(
        experiment_seed=Seed(value=13),
        clustering_identity=StageFingerprint(value="a" * 64),
        profile=_canonical_b4_profile(),
    )
    request = B4ClusteringRequest(
        calibration_scores=score_set,
        clustering=specification,
        eligible_clients=eligible_clients,
    )
    strategy = ExactB4ClusteringStrategy(reader=_SyntheticScoreReader(values=values))

    first = strategy.cluster(request)
    second = strategy.cluster(request)

    assert first == second
    assert adjusted_rand_index(first=first, second=second) == 1.0
    assert tuple(entry.cluster_index for entry in first.assignments) == (1, 0, 1, 1, 2, 2)

    invalid_specification = B4ClusteringSpec(
        experiment_seed=Seed(value=13),
        clustering_identity=StageFingerprint(value="f" * 64),
        profile=_canonical_b4_profile(),
    )
    object.__setattr__(invalid_specification, "n_init", KMeansInitializationCount(value=1))
    invalid_request = B4ClusteringRequest(
        calibration_scores=score_set,
        clustering=invalid_specification,
        eligible_clients=eligible_clients,
    )
    with pytest.raises(ThresholdError, match="locked canonical specification"):
        strategy.cluster(invalid_request)


@dataclass(frozen=True, slots=True, kw_only=True)
class _FamilyMemberships:
    first: ClientId
    second: ClientId
    third: ClientId

    def members(self, *, family_manifest: str, client_id: ClientId) -> tuple[ClientId, ...]:
        del family_manifest
        if client_id in {self.first, self.second}:
            return (self.first, self.second)
        return (self.third,)


@dataclass(frozen=True, slots=True, kw_only=True)
class _ClusterAssignments:
    artifact: ClusterAssignmentArtifact

    def read(self, *, assignment_identity: str) -> ClusterAssignmentArtifact:
        del assignment_identity
        return self.artifact


@dataclass(frozen=True, slots=True, kw_only=True)
class _StrategyContext:
    score_set: CalibrationScoreArtifactSet
    eligible: EligibleClientSet
    reader: _SyntheticScoreReader
    percentile: ThresholdPercentile
    identity: StageFingerprint
    assignments: _ClusterAssignments
    family: _FamilyMemberships


def _strategy_context() -> _StrategyContext:
    values = ((1.0, 2.0), (3.0, 4.0), (5.0, 6.0))
    score_set, eligible = calibration_scores_for_clients(values)
    reader = _SyntheticScoreReader(values=values)
    percentile = ThresholdPercentile(value=Decimal("0.5"))
    identity = StageFingerprint(value="b" * 64)
    cluster_assignments = _cluster_assignment(score_set=score_set, identity=identity)
    assignments = _ClusterAssignments(artifact=cluster_assignments)
    family = _FamilyMemberships(
        first=eligible.roster.client_ids[0], second=eligible.roster.client_ids[1], third=eligible.roster.client_ids[2]
    )
    return _StrategyContext(
        score_set=score_set,
        eligible=eligible,
        reader=reader,
        percentile=percentile,
        identity=identity,
        assignments=assignments,
        family=family,
    )


@pytest.mark.integration
def test_shared_local_and_family_strategies_use_their_locked_identity_and_scores() -> None:
    context = _strategy_context()
    shared = SharedThresholdStrategy(reader=context.reader).assign(
        _request(
            context=context,
            construction=SharedThresholdSpec(
                kind=ThresholdConstructionKind.SHARED,
                percentile=context.percentile,
                construction=SharedThresholdConstruction.MEAN,
                estimator=QuantileEstimatorType.LOCAL_EXACT,
            ),
            policy=CoreThresholdPolicy.B1,
        )
    )
    local = LocalThresholdStrategy(reader=context.reader).assign(
        _request(
            context=context,
            construction=LocalThresholdSpec(
                kind=ThresholdConstructionKind.LOCAL,
                percentile=context.percentile,
                estimator=QuantileEstimatorType.LOCAL_EXACT,
            ),
            policy=CoreThresholdPolicy.B2,
        )
    )
    family_assignment = FamilyThresholdStrategy(reader=context.reader, family_memberships=context.family).assign(
        _request(
            context=context,
            construction=FamilyThresholdSpec(
                kind=ThresholdConstructionKind.FAMILY,
                percentile=context.percentile,
                family_manifest_identity=context.identity,
            ),
            policy=CoreThresholdPolicy.B3,
        )
    )
    assert _values(shared) == (3.0, 3.0, 3.0)
    assert _values(local) == (1.0, 3.0, 5.0)
    assert _values(family_assignment) == (2.0, 2.0, 5.0)


@pytest.mark.integration
def test_b1_shared_mean_excludes_an_ineligible_client() -> None:
    context = _strategy_context()
    excluded_client = context.eligible.roster.client_ids[2]
    partial_eligible = EligibleClientSet(
        roster=context.eligible.roster,
        protocol_eligibility_rule_identity=context.eligible.protocol_eligibility_rule_identity,
        eligible_clients=context.eligible.roster.client_ids[:2],
        ineligible_reasons=(
            IneligibleClientReason(
                client_id=excluded_client, reason=ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK
            ),
        ),
        identity=StageFingerprint(value="9" * 64),
    )
    partial_context = _StrategyContext(
        score_set=context.score_set,
        eligible=partial_eligible,
        reader=context.reader,
        percentile=context.percentile,
        identity=context.identity,
        assignments=context.assignments,
        family=context.family,
    )

    shared = SharedThresholdStrategy(reader=context.reader).assign(
        _request(
            context=partial_context,
            construction=SharedThresholdSpec(
                kind=ThresholdConstructionKind.SHARED,
                percentile=context.percentile,
                construction=SharedThresholdConstruction.MEAN,
                estimator=QuantileEstimatorType.LOCAL_EXACT,
            ),
            policy=CoreThresholdPolicy.B1,
        )
    )

    # Client-02's local threshold (5.0) is excluded; the mean uses only client-00 (1.0) and client-01 (3.0).
    assert _values(shared) == (2.0, 2.0, 2.0)


@dataclass(frozen=True, slots=True, kw_only=True)
class _OtherOnlyFamilyMemberships:
    """A family manifest whose members never include the querying client itself."""

    other: ClientId

    def members(self, *, family_manifest: str, client_id: ClientId) -> tuple[ClientId, ...]:
        del family_manifest, client_id
        return (self.other,)


@pytest.mark.integration
def test_b3_family_construction_rejects_a_family_with_no_eligible_members() -> None:
    context = _strategy_context()
    querying_client = context.family.first
    ineligible_family_member = context.family.second
    eligible_clients = EligibleClientSet(
        roster=context.eligible.roster,
        protocol_eligibility_rule_identity=context.eligible.protocol_eligibility_rule_identity,
        eligible_clients=(querying_client,),
        ineligible_reasons=tuple(
            IneligibleClientReason(
                client_id=client_id, reason=ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK
            )
            for client_id in context.eligible.roster.client_ids
            if client_id != querying_client
        ),
        identity=StageFingerprint(value="8" * 64),
    )
    empty_family_context = _StrategyContext(
        score_set=context.score_set,
        eligible=eligible_clients,
        reader=context.reader,
        percentile=context.percentile,
        identity=context.identity,
        assignments=context.assignments,
        family=context.family,
    )

    with pytest.raises(ThresholdError, match="no eligible family members"):
        FamilyThresholdStrategy(
            reader=context.reader,
            family_memberships=_OtherOnlyFamilyMemberships(other=ineligible_family_member),
        ).assign(
            _request(
                context=empty_family_context,
                construction=FamilyThresholdSpec(
                    kind=ThresholdConstructionKind.FAMILY,
                    percentile=context.percentile,
                    family_manifest_identity=context.identity,
                ),
                policy=CoreThresholdPolicy.B3,
            )
        )


@pytest.mark.integration
def test_cluster_strategy_uses_the_locked_identity_and_scores() -> None:
    context = _strategy_context()
    cluster = ClusterThresholdStrategy(reader=context.reader, assignments=context.assignments).assign(
        _request(
            context=context,
            construction=ClusterThresholdSpec(
                kind=ThresholdConstructionKind.CLUSTER,
                percentile=context.percentile,
                clustering=B4ClusteringSpec(
                    experiment_seed=Seed(value=9), clustering_identity=context.identity, profile=_canonical_b4_profile()
                ),
                aggregation=ClusterThresholdAggregationSpec(
                    percentile=context.percentile,
                    member_local_thresholds=(ThresholdValue(value=1),),
                    cluster_assignment_identity=context.identity,
                ),
            ),
            policy=CoreThresholdPolicy.B4,
        )
    )
    assert _values(cluster) == (2.0, 2.0, 5.0)


@pytest.mark.integration
def test_shrinkage_and_fallback_variants_use_their_locked_identity_and_scores() -> None:
    context = _strategy_context()
    variants = VariantThresholdStrategy(reader=context.reader, assignments=context.assignments)
    shrinkage = variants.assign(
        _request(
            context=context,
            construction=ShrinkageThresholdSpec(
                kind=ThresholdConstructionKind.SHRINKAGE,
                percentile=context.percentile,
                shrinkage_weight=ShrinkageWeight(value=1),
            ),
            policy=ThresholdVariant.SHRINKAGE_LGS,
        )
    )
    fallback = variants.assign(
        _request(
            context=context,
            construction=CalibrationSizeFallbackThresholdSpec(
                kind=ThresholdConstructionKind.CALIB_SIZE_FALLBACK,
                percentile=context.percentile,
                fallback_rule_version="locked-v1",
                calibration_sample_count=CalibrationSampleCount(value=100),
            ),
            policy=ThresholdVariant.CALIB_SIZE_FALLBACK,
        )
    )
    assert _values(shrinkage) == (1.0, 3.0, 5.0)
    assert _values(fallback) == (1.0, 3.0, 5.0)


@pytest.mark.integration
def test_conformal_and_robust_variants_use_their_locked_identity_and_scores() -> None:
    context = _strategy_context()
    variants = VariantThresholdStrategy(reader=context.reader, assignments=context.assignments)
    conformal = variants.assign(
        _request(
            context=context,
            construction=ConformalThresholdSpec(
                kind=ThresholdConstructionKind.CONFORMAL,
                conformal_split=_conformal_split(percentile=context.percentile),
                mode=ConformalMode.SPLIT,
            ),
            policy=ThresholdVariant.CONFORMAL_B2,
        )
    )
    robust = variants.assign(
        _request(
            context=context,
            construction=RobustClusterMedianThresholdSpec(
                kind=ThresholdConstructionKind.ROBUST_CLUSTER_MEDIAN,
                canonical_assignment_identity=context.identity,
            ),
            policy=ThresholdVariant.ROBUST_CLUSTER_MEDIAN_B4,
        )
    )
    assert _values(conformal) == (2.0, 4.0, 6.0)
    assert _values(robust) == (3.0, 3.0, 5.0)


@pytest.mark.integration
def test_fed_stats_strategy_uses_its_locked_identity_and_scores() -> None:
    context = _strategy_context()
    fed_stats = FedStatsThresholdStrategy(reader=context.reader).assign(
        _request(
            context=context,
            construction=FedStatsBenignThresholdSpec(kind=ThresholdConstructionKind.FED_STATS_BENIGN),
            policy=ThresholdComparatorRole.FED_STATS_BENIGN,
        )
    )
    assert len(set(_values(fed_stats))) == 1


@pytest.mark.integration
def test_fed_stats_rejects_an_unrelated_declared_policy() -> None:
    context = _strategy_context()
    strategy = FedStatsThresholdStrategy(reader=context.reader)
    request = _request(
        context=context,
        construction=FedStatsBenignThresholdSpec(kind=ThresholdConstructionKind.FED_STATS_BENIGN),
        policy=CoreThresholdPolicy.B1,
    )
    with pytest.raises(ThresholdError, match="declared policy"):
        strategy.assign(request)


def _request(
    *,
    context: _StrategyContext,
    construction: ThresholdConstructionSpec,
    policy: CoreThresholdPolicy | ThresholdVariant | ThresholdComparatorRole,
) -> AssignThresholdRequest:
    return AssignThresholdRequest(
        calibration_scores=context.score_set,
        construction=construction,
        eligible_clients=context.eligible,
        assignment_metadata=ThresholdAssignmentMetadata(
            policy=policy,
            threshold_identity=ThresholdIdentity(value=StageFingerprint(value="c" * 64)),
            fallback_fingerprint=StageFingerprint(value="d" * 64),
            fpr_target=FprTarget.from_percentile(percentile=context.percentile),
        ),
    )


def _cluster_assignment(
    *, score_set: CalibrationScoreArtifactSet, identity: StageFingerprint
) -> ClusterAssignmentArtifact:
    clients = score_set.per_client.values.roster.client_ids
    fingerprint = ScaledB4Fingerprint(mean=0, standard_deviation=0, skew=0, p95=0)
    return ClusterAssignmentArtifact(
        clustering_identity=identity,
        assignments=tuple(
            ClusterAssignmentEntry(client_id=client, cluster_index=index // 2) for index, client in enumerate(clients)
        ),
        scaled_fingerprints=tuple(
            ScaledFingerprintReference(client_id=client, fingerprint=fingerprint) for client in clients
        ),
        centroid_references=tuple(
            ClusterCentroidReference(cluster_index=index, fingerprint=fingerprint) for index in range(3)
        ),
        content_hash="e" * 64,
    )


def _conformal_split(*, percentile: ThresholdPercentile) -> ConformalSplitSpec:
    partition = StageFingerprint(value="f" * 64)
    return ConformalSplitSpec(
        proper_fit_split=TrainingSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="0" * 64)),
            partition_identity=PartitionIdentity(value=partition),
        ),
        calibration_split=BenignCalibrationSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="1" * 64)),
            partition_identity=PartitionIdentity(value=partition),
        ),
        percentile=percentile,
        alpha=FprTarget.from_percentile(percentile=percentile),
        quantile_index_rule=ConformalQuantileIndexRule.CEILING_N_PLUS_ONE,
    )


def _values(assignment: ThresholdAssignment) -> tuple[float, ...]:
    return tuple(entry.value.value for entry in assignment.per_client_tau.values.entries)
