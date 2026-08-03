"""Pytest plugin that skips only CUDA-dependent tests on CPU-only runners."""

from pathlib import PurePosixPath

import pytest
import torch

_CUDA_ONLY_MODULES = frozenset(
    {
        "tests/integration/centralized_reference/test_centralized_reference_pipeline.py",
        "tests/integration/learning/test_ditto_training.py",
        "tests/integration/learning/test_fedavg_training.py",
        "tests/integration/learning/test_fedprox_training.py",
        "tests/integration/scoring/test_score_reuse_across_thresholds.py",
        "tests/unit/centralized_reference/test_evaluation.py",
        "tests/unit/orchestration/stages/test_federated_training_stages.py",
        "tests/unit/scoring/test_generation.py",
    }
)

_CUDA_ONLY_TESTS = frozenset(
    {
        "tests/scientific/test_fixed_detector_contract.py::test_every_simulated_threshold_method_reads_one_model_and_score_checksum",
        "tests/scientific/test_fixed_detector_contract.py::test_auroc_style_quality_control_is_invariant_across_repeated_reads",
        "tests/unit/centralized_reference/test_checkpointing.py::test_retains_declared_checkpoint_candidates",
        "tests/unit/centralized_reference/test_checkpointing.py::test_selection_uses_fixed_terminal_maximum_round",
        "tests/unit/centralized_reference/test_checkpointing.py::test_selection_rejects_held_out_metrics",
        "tests/unit/centralized_reference/test_scoring.py::test_deterministic_scoring_and_reload",
        "tests/unit/centralized_reference/test_scoring.py::test_score_polarity_higher_is_more_anomalous",
        "tests/unit/centralized_reference/test_thresholding.py::test_pooled_benign_quantile_matches_numpy_linear",
        "tests/unit/centralized_reference/test_training.py::test_deterministic_cuda_training_and_safetensors_reload",
        "tests/unit/centralized_reference/test_training.py::test_training_rejects_undersized_batch",
        "tests/unit/centralized_reference/test_training.py::test_autoencoder_round_trip_shape",
        "tests/unit/learning/federated/test_checkpointing.py::test_retain_checkpoint_candidates_persists_and_reloads",
        "tests/unit/learning/federated/test_checkpointing.py::test_select_checkpoint_chooses_maximum_round",
        "tests/unit/learning/federated/test_checkpointing.py::test_select_checkpoint_rejects_held_out_metrics",
        "tests/unit/learning/federated/test_checkpointing.py::test_select_checkpoint_rejects_attack_labels",
        "tests/unit/learning/federated/test_checkpointing.py::test_retain_checkpoint_candidates_rejects_missing_declared_round",
        "tests/unit/learning/federated/test_checkpointing.py::test_select_checkpoint_rejects_missing_tensor_file",
        "tests/unit/learning/federated/test_checkpointing.py::test_validate_candidate_coordinates_rejects_mismatched_client",
        "tests/unit/learning/federated/test_checkpointing.py::test_rebase_checkpoint_candidates_rejects_target_checksum_mismatch",
        "tests/unit/learning/federated/test_ditto.py::test_train_ditto_produces_distinct_global_and_personalized_checkpoints",
        "tests/unit/learning/federated/test_ditto.py::test_train_ditto_never_aggregates_personalized_states_into_global",
        "tests/unit/learning/federated/test_ditto.py::test_train_ditto_personalized_states_differ_by_client",
        "tests/unit/learning/federated/test_ditto.py::test_train_ditto_personalized_states_persist_across_rounds",
        "tests/unit/learning/federated/test_ditto.py::test_train_ditto_records_personalized_state_references_every_round",
        "tests/unit/learning/federated/test_fedavg.py::test_train_fedavg_produces_history_with_full_participation_every_round",
        "tests/unit/learning/federated/test_fedavg.py::test_train_fedavg_produces_one_checkpoint_candidate_per_declared_round",
        "tests/unit/learning/federated/test_fedavg.py::test_train_fedavg_is_deterministic_given_the_same_seed",
        "tests/unit/learning/federated/test_fedavg.py::test_train_fedavg_never_trains_on_attack_labelled_rows",
        "tests/unit/learning/federated/test_fedprox.py::test_train_fedprox_produces_independent_model_per_coefficient",
        "tests/unit/learning/federated/test_training.py::test_run_local_epoch_returns_full_state_and_positive_sample_count",
        "tests/unit/learning/federated/test_training.py::test_run_local_epoch_with_larger_proximal_coefficient_stays_closer_to_reference",
        "tests/unit/learning/federated/test_training.py::test_proximal_penalty_is_zero_when_parameters_match",
        "tests/unit/learning/federated/test_training.py::test_proximal_penalty_scales_with_coefficient",
        "tests/unit/orchestration/stages/test_centralized_reference_stages.py::test_train_score_threshold_evaluate_stage_chain",
        "tests/unit/runtime/test_compute_and_determinism.py::test_cuda_device_resolution_never_falls_back_to_cpu",
        "tests/unit/runtime/test_compute_and_determinism.py::test_deterministic_cuda_setup_and_worker_seed_derivation",
        "tests/unit/runtime/test_compute_and_determinism.py::test_cuda_tensor_smoke",
    }
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
