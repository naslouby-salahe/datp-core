from datp_core.presentation.population_capabilities import render_population_capability_table


def test_population_capability_table_contains_all_locked_population_boundaries() -> None:
    rendered = render_population_capability_table()

    assert "`NBAIOT_NATURAL_DEVICES`" in rendered
    assert "`CICIOT_FILE_CLIENTS`" in rendered
    assert "`NBAIOT_DIRICHLET_CLIENTS`" in rendered
    assert "`EDGE_SENSOR_CLIENTS`" in rendered
    assert "`EDGE_TEMPORAL_CLIENTS`" in rendered
    assert "sole confirmatory + principal mechanism" in rendered
    assert "small client population" in rendered
