from enum import Enum

import pytest

from datp_core.domain import clients, datasets, metrics, partitions, policies, regimes, seeds
from datp_core.domain.metrics import Metric, MetricRole
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime, RegimeRole
from datp_core.domain.seeds import SeedPlan, SeedPlanError, SeedRole

DOMAIN_MODULES = (clients, datasets, metrics, partitions, policies, regimes, seeds)

FORBIDDEN_STALE_TOKENS = ("B5", "B3-LGS", "B3_LGS", "local_head", "LocalHead")


def test_all_enum_values_are_stable():
    assert [p.value for p in ThresholdPolicy] == ["B0", "B1", "B2", "B3", "B4"]
    assert [r.value for r in Regime] == ["A", "B_A", "B_B_REJECTED_NO_METADATA", "C", "D", "D_TEMPORAL"]
    assert [d.value for d in datasets.DatasetId] == ["nbaiot", "ciciot2023", "edge_iiotset"]


def test_no_stale_labels_in_enum_identifiers():
    for module in DOMAIN_MODULES:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Enum):
                for member in attr:
                    for token in FORBIDDEN_STALE_TOKENS:
                        label = f"{attr}.{member.name}"
                        assert token not in member.name, f"{label} contains stale token {token!r}"
                        assert token not in str(member.value), f"{label} value contains stale token {token!r}"


def test_no_stale_local_head_placeholder_exists():
    for member in TrainingAlgorithm:
        assert "local_head" not in member.value
        assert "local_head" not in member.name.lower()


def test_ditto_fallback_naming_rule_is_representable():
    assert TrainingAlgorithm.DITTO in TrainingAlgorithm
    assert TrainingAlgorithm.PERSONALIZED_FEDREP_AE in policies.PERSONALIZATION_FALLBACKS
    assert TrainingAlgorithm.PERSONALIZED_FEDPER_AE in policies.PERSONALIZATION_FALLBACKS
    assert TrainingAlgorithm.DITTO not in policies.PERSONALIZATION_FALLBACKS


def test_metric_claim_roles_are_correct():
    assert metrics.metric_spec(Metric.CV_FPR).role is MetricRole.PRIMARY
    assert metrics.metric_spec(Metric.CV_FPR).is_thresholding_verdict is True
    assert metrics.metric_spec(Metric.AUROC).role is MetricRole.CONTROL


def test_auroc_is_marked_control_only():
    assert metrics.is_control(Metric.AUROC)
    assert not metrics.is_primary(Metric.AUROC)
    assert not metrics.is_thresholding_verdict(Metric.AUROC)


def test_regime_a_is_marked_confirmatory():
    assert regimes.regime_spec(Regime.A).role is RegimeRole.CONFIRMATORY
    assert regimes.CONFIRMATORY_REGIMES == (Regime.A,)


def test_regime_d_is_marked_external_validation_only():
    assert regimes.regime_spec(Regime.D).role is RegimeRole.EXTERNAL_VALIDATION
    assert regimes.regime_spec(Regime.D).role is not RegimeRole.CONFIRMATORY


def test_fedprox_and_personalization_are_outside_causal_ladder():
    assert Comparator.FEDPROX in policies.STRESS_TEST_COMPARATORS
    assert Comparator.DITTO in policies.STRESS_TEST_COMPARATORS
    assert Comparator.FEDREP_AE in policies.STRESS_TEST_COMPARATORS
    assert Comparator.FEDPER_AE in policies.STRESS_TEST_COMPARATORS
    assert TrainingAlgorithm.FEDPROX not in (policies.CORE_LADDER_TRAINING_ALGORITHM,)


def test_b0_excluded_from_core_causal_ladder():
    assert ThresholdPolicy.B0 not in policies.CORE_CAUSAL_LADDER
    assert set(policies.CORE_CAUSAL_LADDER) == {
        ThresholdPolicy.B1,
        ThresholdPolicy.B2,
        ThresholdPolicy.B3,
        ThresholdPolicy.B4,
    }


def test_b4_canonical_k_is_3():
    assert policies.B4_CANONICAL_K == 3
    assert policies.B4_FINGERPRINT_FIELDS == ("mean", "std", "skewness", "p95")


def test_client_id_requires_nonempty_value():
    with pytest.raises(ValueError):
        clients.ClientId(value="", identity_type=clients.ClientIdentityType.PHYSICAL_DEVICE)


def test_split_ratios_must_sum_to_one():
    partitions.SplitRatios(train=0.6, calibration=0.2, test=0.18, train_calibration_gap=0.01, calibration_test_gap=0.01)
    with pytest.raises(ValueError):
        partitions.SplitRatios(train=0.6, calibration=0.2, test=0.1)


def test_calibration_eligibility_threshold():
    assert partitions.is_calibration_eligible(100)
    assert not partitions.is_calibration_eligible(99)


def test_seed_plan_locked_confirmatory_set():
    plan = seeds.confirmatory_seed_plan()
    assert plan.seeds == tuple(range(10))
    assert seeds.PRELIMINARY_SEEDS == tuple(range(5))


def test_seed_plan_rejects_duplicates_and_empty():
    with pytest.raises(SeedPlanError):
        SeedPlan(seeds=(0, 0, 1), role=SeedRole.ANALYSIS)
    with pytest.raises(SeedPlanError):
        SeedPlan(seeds=(), role=SeedRole.ANALYSIS)


def test_paired_delta_seeds_requires_matching_plans():
    plan_a = SeedPlan(seeds=(0, 1, 2), role=SeedRole.ANALYSIS)
    plan_b = SeedPlan(seeds=(0, 1, 2), role=SeedRole.TRAIN)
    assert seeds.paired_delta_seeds(plan_a, plan_b) == (0, 1, 2)
    mismatched = SeedPlan(seeds=(0, 1), role=SeedRole.ANALYSIS)
    with pytest.raises(SeedPlanError):
        seeds.paired_delta_seeds(plan_a, mismatched)
