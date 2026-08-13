from datp_core.presentation.prior_art import render_prior_art_collision_table, render_prior_art_distinction_table


def test_prior_art_collision_table_retains_every_roadmap_collision_and_unexecuted_gate() -> None:
    table = render_prior_art_collision_table()

    assert table.count("\n| ") == 21
    assert "Meidan et al. 2018" in table
    assert "Shahid 2026" in table
    assert "Submission-time novelty gate: `NOT_EXECUTED`" in table


def test_prior_art_distinction_table_preserves_not_reported_source_boundary() -> None:
    table = render_prior_art_distinction_table()

    assert "NOT_REPORTED" in table
    assert "DATP-Core" in table


def test_prior_art_distinction_table_columns_match_roadmap_10_d_9b() -> None:
    lines = render_prior_art_distinction_table().splitlines()
    header = lines[2]
    columns = [cell.strip() for cell in header.strip().strip("|").split("|")]

    assert columns == [
        "Work",
        "Primary calibration object",
        "Detector fixed across the work's threshold/calibration comparison?",
        "Score/probability mapping modified by the calibration method?",
        "Benign-only threshold fitting?",
        "Outcome/class/attack labels used to fit the calibration object?",
        "Shared/federation-wide operating point present?",
        "Client-local operating point present?",
        "Group/cluster operating point present?",
        "Same evaluation population used across compared scopes?",
        "Cross-client FPR dispersion reported as an endpoint?",
        "Formal coverage/risk guarantee?",
        "Adversarial/Byzantine calibration guarantee?",
        "DATP-Core distinction",
    ]

    data_rows = [line for line in lines if line.startswith("| ") and "---" not in line][1:]
    assert len(data_rows) == 13
    assert all(line.count("|") == len(columns) + 1 for line in data_rows)
