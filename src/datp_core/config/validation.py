"""Validation rules protecting catalogue consistency and dependency references."""

from __future__ import annotations

from pathlib import Path

from datp_core.config.resolver import resolve_catalogue
from datp_core.config.yaml_loader import load_protocols_config


def validate_all_configurations(
    experiments_path: Path = Path("configs/experiments.yaml"),
    protocols_path: Path = Path("configs/protocols.yaml"),
) -> None:
    catalogue = resolve_catalogue(experiments_path, protocols_path)
    protocols_cfg = load_protocols_config(protocols_path)

    # 1. Validate that all training, checkpoint, and seed profiles exist
    for exp_id, exp_rec in catalogue.experiments.items():
        if not catalogue.training_profiles.contains(exp_rec.training_profile_id):
            raise ValueError(f"Experiment {exp_id} references missing training profile: {exp_rec.training_profile_id}")
        if not catalogue.checkpoint_profiles.contains(exp_rec.checkpoint_profile_id):
            raise ValueError(
                f"Experiment {exp_id} references missing checkpoint profile: {exp_rec.checkpoint_profile_id}"
            )
        if not catalogue.seed_cohorts.contains(exp_rec.seed_cohort_id):
            raise ValueError(f"Experiment {exp_id} references missing seed cohort: {exp_rec.seed_cohort_id}")

        # 2. Validate threshold policies referenced in evaluations exist in protocols.yaml
        valid_policies = set(protocols_cfg.threshold_policies.keys())
        for eval_spec in exp_rec.evaluations:
            if str(eval_spec.threshold_policy_id) not in valid_policies:
                raise ValueError(
                    f"Experiment {exp_id} references unconfigured threshold policy: {eval_spec.threshold_policy_id}"
                )
