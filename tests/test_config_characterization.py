"""Characterization tests protecting locked scientific counts and YAML structures."""

from pathlib import Path

import yaml


def test_six_authoritative_yaml_documents_exist() -> None:
    config_dir = Path("configs")
    expected_files = {
        config_dir / "datasets" / "ciciot2023.yaml",
        config_dir / "datasets" / "edge_iiotset.yaml",
        config_dir / "datasets" / "nbaiot.yaml",
        config_dir / "experiments.yaml",
        config_dir / "protocols.yaml",
        config_dir / "runtime.yaml",
    }
    for file_path in expected_files:
        assert file_path.exists(), f"Authoritative YAML file missing: {file_path}"


def test_configured_dataset_count() -> None:
    dataset_dir = Path("configs/datasets")
    dataset_files = list(dataset_dir.glob("*.yaml"))
    assert len(dataset_files) == 3, f"Expected exactly 3 dataset YAMLs, found {len(dataset_files)}"

    dataset_ids = set()
    for f in dataset_files:
        content = yaml.safe_load(f.read_text())
        dataset_ids.add(content["dataset"])

    assert dataset_ids == {"ciciot2023", "edge_iiotset", "nbaiot"}


def test_configured_study_population_count() -> None:
    experiments_yaml = Path("configs/experiments.yaml")
    content = yaml.safe_load(experiments_yaml.read_text())
    study_populations = content.get("study_populations", {})
    assert len(study_populations) == 7, f"Expected exactly 7 study populations, found {len(study_populations)}"
    expected_populations = {
        "nbaiot_natural_devices",
        "nbaiot_anchor_natural_devices",
        "nbaiot_dirichlet_heterogeneity",
        "ciciot2023_file_pseudo_clients",
        "edge_iiotset_sensor_groups",
        "edge_iiotset_chronological_groups",
        "edge_iiotset_static_reference_groups",
    }
    assert set(study_populations.keys()) == expected_populations


def test_configured_experiment_count() -> None:
    experiments_yaml = Path("configs/experiments.yaml")
    content = yaml.safe_load(experiments_yaml.read_text())
    experiments = content.get("experiments", [])
    assert len(experiments) == 23, f"Expected exactly 23 experiments, found {len(experiments)}"
    experiment_names = [e["name"] for e in experiments]
    assert len(set(experiment_names)) == 23, "Duplicate experiment names found"


def test_configured_threshold_policy_count() -> None:
    protocols_yaml = Path("configs/protocols.yaml")
    content = yaml.safe_load(protocols_yaml.read_text())
    threshold_policies = content.get("threshold_policies", {})
    assert len(threshold_policies) == 14, f"Expected exactly 14 threshold policies, found {len(threshold_policies)}"
    expected_policies = {
        "shared_mean_p95",
        "shared_pooled_p95",
        "shared_weighted_p95",
        "local_p95",
        "family_p95",
        "centralized_pooled_p95",
        "cluster_k3_mean_p95",
        "cluster_k9_mean_p95",
        "cluster_k3_robust_median_p95",
        "conformal_local_p95",
        "local_global_shrinkage_p95",
        "calibration_size_aware_fallback_p95",
        "federated_summary_matched_exceedance",
        "federated_summary_fixed_k",
    }
    assert set(threshold_policies.keys()) == expected_policies
