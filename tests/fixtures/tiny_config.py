"""Tiny in-memory config dicts matching config/schemas.py shapes, for tests that should not
depend on the real configs/ directory."""

from __future__ import annotations

from typing import Any


def tiny_dataset_config_dict() -> dict[str, Any]:
    return {
        "name": "tiny_fixture_dataset",
        "status": "contract_only",
        "dataset_id": "nbaiot",
        "regimes": ["A"],
        "client_identity_type": "physical_device",
        "raw_subdirectory": "tiny_fixture_dataset",
    }


def tiny_suite_config_dict() -> dict[str, Any]:
    return {
        "name": "tiny_fixture_suite",
        "status": "contract_only",
        "regimes": ["A"],
        "experiment_ids": ["E-FIXTURE"],
        "training_enabled": False,
        "requires_score_reuse": True,
        "allow_training_override": False,
    }
