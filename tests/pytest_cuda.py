"""Pytest plugin that skips only CUDA-dependent tests on CPU-only runners."""

from pathlib import PurePosixPath

import pytest
import torch


def _tests(module: str, *names: str) -> frozenset[str]:
    return frozenset(f"{module}::{name}" for name in names)


_CUDA_ONLY_MODULES = frozenset(
    {
        "tests/e2e/test_centralized_reference_pipeline.py",
        "tests/integration/pipeline/test_centralized_reference.py",
        "tests/integration/learning/test_ditto_training.py",
        "tests/integration/learning/test_fedavg_training.py",
        "tests/integration/learning/test_fedprox_training.py",
        "tests/integration/scoring/test_score_reuse_across_thresholds.py",
        "tests/unit/pipeline/decision/test_centralized_evaluation.py",
        "tests/unit/scoring/test_generation.py",
    }
)

_CUDA_ONLY_TESTS = frozenset().union(
    _tests(
        "tests/scientific/test_fixed_detector_contract.py",
        "test_every_threshold_method_receives_identical_detector_provenance",
        "test_auroc_is_identical_across_independently_generated_score_artifacts",
        "test_rescoring_the_same_frozen_checkpoint_reproduces_byte_identical_score_artifacts",
    ),
    _tests(
        "tests/unit/pipeline/checkpoints/test_centralized_checkpoints.py",
        "test_retains_declared_checkpoint_candidates",
        "test_selection_uses_fixed_terminal_maximum_round",
        "test_selection_rejects_held_out_metrics",
    ),
    _tests(
        "tests/unit/pipeline/scoring/test_centralized_scoring.py",
        "test_deterministic_scoring_and_reload",
        "test_score_polarity_higher_is_more_anomalous",
    ),
    _tests(
        "tests/unit/pipeline/decision/test_centralized_thresholds.py",
        "test_pooled_benign_quantile_matches_declared_linear_quantile",
    ),
    _tests(
        "tests/unit/learning/centralized/test_training.py",
        "test_deterministic_cuda_training_and_safetensors_reload",
        "test_training_rejects_undersized_batch",
        "test_autoencoder_round_trip_shape",
    ),
    _tests(
        "tests/unit/learning/federated/test_checkpointing.py",
        "test_retain_checkpoint_candidates_persists_and_reloads",
        "test_select_checkpoint_chooses_maximum_round",
        "test_select_checkpoint_rejects_held_out_metrics",
        "test_select_checkpoint_rejects_attack_labels",
        "test_retain_checkpoint_candidates_rejects_missing_declared_round",
        "test_select_checkpoint_rejects_missing_tensor_file",
        "test_validate_candidate_coordinates_rejects_mismatched_client",
        "test_rebase_checkpoint_candidates_rejects_target_checksum_mismatch",
    ),
    _tests(
        "tests/unit/learning/federated/test_ditto.py",
        "test_train_ditto_produces_distinct_global_and_personalized_checkpoints",
        "test_train_ditto_never_aggregates_personalized_states_into_global",
        "test_train_ditto_personalized_states_differ_by_client",
        "test_train_ditto_personalized_states_persist_across_rounds",
        "test_train_ditto_records_personalized_state_references_every_round",
        "test_ditto_markers_without_valid_artifacts_are_not_reusable",
    ),
    _tests(
        "tests/unit/learning/federated/test_fedavg.py",
        "test_train_fedavg_produces_history_with_full_participation_every_round",
        "test_train_fedavg_produces_one_checkpoint_candidate_per_declared_round",
        "test_train_fedavg_is_deterministic_given_the_same_seed",
        "test_train_fedavg_never_trains_on_attack_labelled_rows",
    ),
    _tests(
        "tests/unit/learning/federated/test_fedprox.py",
        "test_train_fedprox_produces_independent_model_per_coefficient",
    ),
    _tests(
        "tests/unit/learning/federated/test_training.py",
        "test_run_local_epoch_returns_full_state_and_positive_sample_count",
        "test_run_local_epoch_with_larger_proximal_coefficient_stays_closer_to_reference",
        "test_proximal_penalty_is_zero_when_parameters_match",
        "test_proximal_penalty_scales_with_coefficient",
    ),
    _tests(
        "tests/unit/runtime/test_compute_and_determinism.py",
        "test_cuda_device_resolution_never_falls_back_to_cpu",
        "test_deterministic_cuda_setup_and_worker_seed_derivation",
        "test_cuda_tensor_smoke",
    ),
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "cuda: requires an available CUDA device")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if torch.cuda.is_available():
        return
    skip = pytest.mark.skip(reason="CUDA-required test skipped on a CPU-only runner")
    for item in items:
        node_id = item.nodeid.split("[", maxsplit=1)[0]
        module = PurePosixPath(node_id.split("::", maxsplit=1)[0]).as_posix()
        if module in _CUDA_ONLY_MODULES or node_id in _CUDA_ONLY_TESTS:
            item.add_marker(skip)
            item.add_marker("cuda")
