from pathlib import Path

import pytest
from datp_core.anchor.models import HistoricalMetricArtifactSource
from datp_core.anchor.reproduction import (
    ANCHOR_CHECKPOINT_STATUS,
    ANCHOR_METRIC,
    ANCHOR_POPULATION,
    ANCHOR_TRAINING_MODEL,
    historical_sources_for_seed_directories,
    load_historical_observations,
    references_from_protocol,
    reproduce_anchor,
    validate_historical_seed_cohort,
)
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL, HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from tests.unit.anchor.helpers import make_observation, matching_anchor_observations

from datp_core.core.errors import AnchorReproductionError
from datp_core.core.identifiers import CheckpointStatus, FederatedThresholdMethod, MetricId
from datp_core.core.numeric import Seed


def test_historical_cohort_is_exactly_five_seeds() -> None:
    cohort = validate_historical_seed_cohort(HISTORICAL_ANCHOR_SEED_COHORT)
    assert cohort.member_count.value == 5
    assert [seed.value for seed in cohort.values] == [0, 1, 2, 3, 4]


def test_confirmatory_ten_seed_cohort_is_rejected() -> None:
    with pytest.raises(AnchorReproductionError, match="ten-seed"):
        validate_historical_seed_cohort(CONFIRMATORY_SEED_COHORT)


def test_duplicate_seed_cohort_is_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        SeedCohort(values=(Seed(0), Seed(0), Seed(1), Seed(2), Seed(3)))


def test_exact_reproduction_has_no_discrepancies() -> None:
    result = reproduce_anchor(observations=matching_anchor_observations())
    assert result.seed_cohort == HISTORICAL_ANCHOR_SEED_COHORT
    assert len(result.references) == 10
    assert len(result.metric_comparisons) == 10
    assert result.discrepancies == ()
    assert all(item.decision.value == "equivalent" for item in result.metric_comparisons)


def test_missing_mandatory_metric_blocks() -> None:
    observations = matching_anchor_observations()[:-1]
    result = reproduce_anchor(observations=observations)
    assert any(item.reason.value == "missing_mandatory_observation" for item in result.discrepancies)


def test_wrong_seed_subset_blocks() -> None:
    observations = tuple(
        make_observation(
            seed=Seed(seed),
            population=ANCHOR_POPULATION,
            training_model=ANCHOR_TRAINING_MODEL,
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            metric=ANCHOR_METRIC,
            checkpoint_status=ANCHOR_CHECKPOINT_STATUS,
        )
        for seed in (0, 1, 2)
    )
    result = reproduce_anchor(observations=observations)
    assert result.seed_subset_comparison.reason is not None
    assert result.seed_subset_comparison.reason.value == "wrong_seed_subset"


def test_confirmatory_only_seeds_raise() -> None:
    with pytest.raises(AnchorReproductionError, match="confirmatory-only"):
        reproduce_anchor(observations=(make_observation(seed=Seed(9)),))


def test_non_historical_checkpoint_semantics_cannot_enter_reproduction() -> None:
    observations = list(matching_anchor_observations())
    first = observations[0]
    observations[0] = make_observation(
        seed=first.seed,
        value=first.value.value,
        threshold_method=first.threshold_method,
        checkpoint_status=CheckpointStatus.CANDIDATE,
    )
    with pytest.raises(AnchorReproductionError, match="checkpoint"):
        reproduce_anchor(observations=tuple(observations))


def test_protocol_references_use_metric_specific_absolute_tolerance() -> None:
    references = references_from_protocol(ANCHOR_DECISION_PROTOCOL)
    assert len(references) == 10
    assert all(item.tolerance_rule.strategy.value == "absolute_tolerance" for item in references)
    assert all(item.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION for item in references)


def test_historical_source_loader_rejects_missing_artifact(tmp_path: Path) -> None:
    source = HistoricalMetricArtifactSource(
        path=tmp_path / "missing.json",
        seed=Seed(0),
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
    )
    with pytest.raises(AnchorReproductionError, match="missing"):
        load_historical_observations((source,))


def test_stale_artifact_schema_blocks(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text('{"seed": 0, "cv_fpr": 1.0}', encoding="utf-8")
    source = HistoricalMetricArtifactSource(
        path=path,
        seed=Seed(0),
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
    )
    with pytest.raises(AnchorReproductionError, match="schema"):
        load_historical_observations((source,))


def test_historical_sources_layout_helper_is_five_by_two() -> None:
    sources = historical_sources_for_seed_directories(Path("shared"), Path("local"))
    assert len(sources) == 10
    assert {source.threshold_method for source in sources} == {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    }
