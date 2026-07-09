import numpy as np
from tests.fixtures.absorption_bands import tiny_absorption_bands
from tests.fixtures.b_fedstats_benign_scores import tiny_fedstats_benign_calibration_scores
from tests.fixtures.tiny_clients import tiny_clients
from tests.fixtures.tiny_config import tiny_dataset_config_dict, tiny_suite_config_dict
from tests.fixtures.tiny_dataset_contract import tiny_dataset_contract
from tests.fixtures.tiny_manifest import tiny_score_manifest
from tests.fixtures.tiny_scores import tiny_benign_scores

_MAX_FIXTURE_ROWS = 32


def test_fixtures_load_without_error():
    assert tiny_clients()
    assert tiny_benign_scores().size > 0
    assert tiny_dataset_contract() is not None
    assert tiny_dataset_config_dict()
    assert tiny_suite_config_dict()
    assert tiny_score_manifest() is not None
    assert tiny_fedstats_benign_calibration_scores()
    assert tiny_absorption_bands()


def test_fixtures_are_deterministic():
    assert tiny_clients() == tiny_clients()
    assert np.array_equal(tiny_benign_scores(), tiny_benign_scores())
    assert tiny_dataset_contract() == tiny_dataset_contract()
    assert tiny_dataset_config_dict() == tiny_dataset_config_dict()
    assert tiny_score_manifest() == tiny_score_manifest()
    first = tiny_fedstats_benign_calibration_scores()
    second = tiny_fedstats_benign_calibration_scores()
    assert first.keys() == second.keys()
    assert all(np.array_equal(first[k], second[k]) for k in first)


def test_fixtures_do_not_require_raw_dataset():
    contract = tiny_dataset_contract()
    assert contract.raw_subdirectory == "tiny_fixture_dataset"
    assert "data/raw" not in contract.raw_subdirectory


def test_fixtures_are_small():
    assert len(tiny_clients()) <= _MAX_FIXTURE_ROWS
    assert tiny_benign_scores().size <= _MAX_FIXTURE_ROWS
    fedstats = tiny_fedstats_benign_calibration_scores()
    assert len(fedstats) <= _MAX_FIXTURE_ROWS
    assert all(v.size <= _MAX_FIXTURE_ROWS for v in fedstats.values())
    assert len(tiny_absorption_bands()) <= _MAX_FIXTURE_ROWS


def test_fixtures_contain_no_scientific_result_claims():
    manifest = tiny_score_manifest()
    assert manifest.common.code_version == "phase1-fixture"
    suite = tiny_suite_config_dict()
    assert suite["experiment_ids"] == ["E-FIXTURE"]
    assert suite["status"] == "contract_only"
