from json import dumps
from pathlib import Path

import pytest

from datp_core.anchor.models import AnchorGateStatus
from datp_core.anchor.reproduction import (
    historical_sources_for_seed_directories,
    load_historical_observations,
    references_from_protocol,
    reproduce_anchor,
    threshold_method_from_historical_scope,
)
from datp_core.domain.enums import ExperimentReadiness, FederatedThresholdMethod
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Seed
from datp_core.orchestration.stages.verify_anchor import VerifyAnchorStageRequest, verify_anchor_stage
from datp_core.protocols.anchor import (
    ANCHOR_DECISION_PROTOCOL,
    HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
    HISTORICAL_SHARED_THRESHOLD_CV_FPR,
)


def _write_metrics(
    path: Path,
    *,
    seed: Seed,
    cv_fpr: float,
    threshold_scope: str,
    checkpoint_identity: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": seed.value,
        "dataset": "nbaiot",
        "regime": "a",
        "threshold_scope": threshold_scope,
        "cv_fpr": cv_fpr,
        "client_count": 9,
        "eligible_count": 9,
        "provenance": {
            "model_checkpoint_identity": checkpoint_identity,
            "score_artifact_identity": "s" * 64,
            "split_manifest_identity": "p" * 64,
            "config_identity": "c" * 64,
            "metric_code_version": "m" * 64,
            "threshold_code_version": "t" * 64,
            "package_version": "v" * 64,
            "generated_at_utc": "2026-05-03T00:00:00+00:00",
        },
        "baseline": "ignored_legacy_token",
        "per_client": [],
    }
    path.write_text(dumps(payload), encoding="utf-8")


def _fixture_roots(tmp_path: Path) -> tuple[Path, Path]:
    shared_root = tmp_path / "shared_threshold"
    local_root = tmp_path / "local_threshold"
    for seed, shared_value, local_value in zip(
        range(5),
        HISTORICAL_SHARED_THRESHOLD_CV_FPR,
        HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
        strict=True,
    ):
        identity = f"{seed:064d}"
        _write_metrics(
            shared_root / f"seed_{seed}" / "metrics.json",
            seed=Seed(seed),
            cv_fpr=shared_value.value,
            threshold_scope="eligible_client_arithmetic_mean",
            checkpoint_identity=identity,
        )
        _write_metrics(
            local_root / f"seed_{seed}" / "metrics.json",
            seed=Seed(seed),
            cv_fpr=local_value.value,
            threshold_scope="per_client_percentile",
            checkpoint_identity=identity,
        )
    return shared_root, local_root


def test_pipeline_loads_historical_artifacts_and_passes_gate(tmp_path: Path) -> None:
    shared_root, local_root = _fixture_roots(tmp_path)
    sources = historical_sources_for_seed_directories(shared_root, local_root)
    observations = load_historical_observations(sources)
    assert len(observations) == 10
    for shared, local in zip(observations[0::2], observations[1::2], strict=True):
        assert shared.model_checkpoint_identity == local.model_checkpoint_identity

    result = verify_anchor_stage(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL, historical_sources=sources, diagnostics_directory=tmp_path / "diag"
        )
    )
    assert result.status.gate_status is AnchorGateStatus.PASS
    assert result.status.dependent_readiness is ExperimentReadiness.DECLARED
    assert result.gate.reproduction.seed_cohort.member_count.value == 5
    assert len(result.gate.reproduction.references) == len(ANCHOR_DECISION_PROTOCOL.references)


def test_pipeline_blocks_stale_mismatched_value(tmp_path: Path) -> None:
    shared_root, local_root = _fixture_roots(tmp_path)
    stale = shared_root / "seed_0" / "metrics.json"
    payload = stale.read_text(encoding="utf-8").replace(
        str(HISTORICAL_SHARED_THRESHOLD_CV_FPR[0].value),
        "9.999999999999999",
        1,
    )
    stale.write_text(payload, encoding="utf-8")
    sources = historical_sources_for_seed_directories(shared_root, local_root)
    result = verify_anchor_stage(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL, historical_sources=sources, diagnostics_directory=tmp_path / "diag"
        )
    )
    assert result.status.gate_status is AnchorGateStatus.BLOCKED
    assert result.gate.reproduction.discrepancies
    assert (tmp_path / "diag" / "anchor_discrepancies.json").exists()


def test_pipeline_rejects_wrong_threshold_scope_token(tmp_path: Path) -> None:
    shared_root, local_root = _fixture_roots(tmp_path)
    path = shared_root / "seed_0" / "metrics.json"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "eligible_client_arithmetic_mean",
            "unknown_threshold_scope",
        ),
        encoding="utf-8",
    )
    sources = historical_sources_for_seed_directories(shared_root, local_root)
    with pytest.raises(AnchorReproductionError):
        load_historical_observations(sources)


def test_historical_scope_tokens_map_only_to_shared_and_local() -> None:
    assert (
        threshold_method_from_historical_scope("eligible_client_arithmetic_mean")
        is FederatedThresholdMethod.SHARED_THRESHOLD
    )
    assert threshold_method_from_historical_scope("per_client_percentile") is FederatedThresholdMethod.LOCAL_THRESHOLD


def test_references_and_fixture_observations_are_full_precision_aligned(tmp_path: Path) -> None:
    shared_root, local_root = _fixture_roots(tmp_path)
    observations = load_historical_observations(historical_sources_for_seed_directories(shared_root, local_root))
    reproduction = reproduce_anchor(observations=observations)
    for comparison in reproduction.metric_comparisons:
        assert comparison.observation is not None
        assert comparison.observation.value == comparison.reference.value
        assert comparison.signed_difference == 0.0
    assert [
        item.value
        for item in references_from_protocol()
        if item.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD
    ] == list(HISTORICAL_SHARED_THRESHOLD_CV_FPR)
