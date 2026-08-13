from datp_core.analysis.mechanisms.association import AssociationObservation, heterogeneity_benefit_association
from datp_core.core.identifiers import ExperimentId, PopulationId, RegimeLabel
from datp_core.core.numeric import MetricValue, Seed
from datp_core.presentation.export import _render_association_result


def test_association_report_binds_each_influence_diagnostic_to_its_observation() -> None:
    observations = tuple(
        AssociationObservation(
            seed=Seed(index),
            experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            regime_label=RegimeLabel(f"alpha_{index}"),
            heterogeneity=MetricValue(0.1 + 0.2 * index),
            benefit=MetricValue(0.01 + 0.03 * index),
        )
        for index in range(5)
    )

    rendered = tuple(str(line) for line in _render_association_result(heterogeneity_benefit_association(observations)))

    first_observation = next(line for line in rendered if line.startswith("Observation 1:"))
    assert "seed=0; experiment=controlled_heterogeneity_sweep; " in first_observation
    assert (
        "population=nbaiot_dirichlet_clients; regime=alpha_0; heterogeneity=0.100; benefit=0.010; "
        in first_observation
    )
    assert "leverage=" in first_observation
    assert "leave-one-out slope=" in first_observation
    assert "leave-one-out R²=" in first_observation
    assert "slope influence=" in first_observation


def test_association_report_marks_undefined_leave_one_out_fits_unavailable() -> None:
    observations = tuple(
        AssociationObservation(
            seed=Seed(index),
            experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            regime_label=RegimeLabel(f"alpha_{index}"),
            heterogeneity=MetricValue(0.1 if index < 4 else 0.3),
            benefit=MetricValue(0.01 + index * 0.01),
        )
        for index in range(5)
    )

    result = heterogeneity_benefit_association(observations)

    assert result.statistics is not None
    diagnostics = result.statistics.leave_one_out_diagnostics
    assert diagnostics.slopes[4] is None
    assert diagnostics.r_squared[4] is None
    assert diagnostics.influences[4] is None
    assert diagnostics.unavailable_reasons[4] is not None
    rendered = tuple(str(line) for line in _render_association_result(result))
    assert any(
        "Observation 5:" in line and "slope influence=unavailable (leave-one-out regression is undefined" in line
        for line in rendered
    )
