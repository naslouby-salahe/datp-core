import pytest

from datp_core.cli import _COMMANDS, main


def test_cli_help_works(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "datp-core" in captured.out


def test_doctor_works_without_raw_datasets_and_reports_missing_data(capsys):
    exit_code = main(["doctor"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "MISSING" in captured.out


def test_validate_config_works_on_skeleton_configs(capsys):
    exit_code = main(["validate-config"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK   configs/datasets/nbaiot.yaml" in captured.out
    assert "FAIL" not in captured.out


def test_show_paths_prints_canonical_roots(capsys):
    exit_code = main(["show-paths"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "repo_root:" in captured.out
    assert "outputs:" in captured.out
    assert "checkpoints:" in captured.out
    assert "results:" in captured.out


def test_list_suites_lists_suite_configs(capsys):
    exit_code = main(["list-suites"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "confirmatory_regime_a: status=contract_only runnable=False" in captured.out
    assert "full_journal: status=contract_only runnable=False" in captured.out


def test_validate_layout_reports_ok_on_the_real_repo(capsys):
    exit_code = main(["validate-layout"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "layout: OK" in captured.out


def test_training_command_is_absent_during_phase1():
    assert "train" not in _COMMANDS
    with pytest.raises(SystemExit):
        main(["train"])
