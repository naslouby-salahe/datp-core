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
