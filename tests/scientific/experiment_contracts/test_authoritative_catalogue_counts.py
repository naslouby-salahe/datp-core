"""Locked catalogue cardinality and identity invariants."""

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
    assert all(path.exists() for path in expected_files)


def test_configured_dataset_population_experiment_and_policy_catalogues_are_locked() -> None:
    config_dir = Path("configs")
    dataset_ids = {yaml.safe_load(path.read_text())["dataset"] for path in (config_dir / "datasets").glob("*.yaml")}
    assert dataset_ids == {"ciciot2023", "edge_iiotset", "nbaiot"}
    experiments = yaml.safe_load((config_dir / "experiments.yaml").read_text())
    assert len(experiments["study_populations"]) == 7
    assert len(experiments["experiments"]) == 23
    assert len({entry["name"] for entry in experiments["experiments"]}) == 23
    assert len(yaml.safe_load((config_dir / "protocols.yaml").read_text())["threshold_policies"]) == 14
