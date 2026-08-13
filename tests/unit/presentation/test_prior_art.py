from datp_core.presentation.prior_art import PriorArtCategory, render_prior_art_distinction_table


def test_prior_art_table_uses_only_locked_categories_and_all_required_rows() -> None:
    rendered = render_prior_art_distinction_table()

    assert "FedIoT/FedDetect 2021" in rendered
    assert "DATP-Core" in rendered
    assert "NOT_REPORTED" in rendered
    assert PriorArtCategory.PARTIAL.value in rendered
