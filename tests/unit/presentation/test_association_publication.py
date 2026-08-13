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
        for index in range(3)
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
