from pathlib import Path

from datp_core.domain.enums import DatasetId, PopulationId, SplitProtocolId
from datp_core.domain.values import Seed
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PreprocessingHandoffRequest,
    build_preprocessing_handoff,
    construct_population,
)
from datp_core.populations.models import iid_condition


def test_end_to_end_manifest_handoff_for_natural_and_dirichlet(nbaiot_canonical_root: Path) -> None:
    natural = construct_population(
        PopulationConstructionRequest(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            nbaiot_canonical_root,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            None,
        )
    )
    handoff = build_preprocessing_handoff(
        PreprocessingHandoffRequest(
            natural,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            DatasetId.NBAIOT,
            deployment_fallback_client_ids=frozenset(),
        )
    )
    assert handoff.population_manifest.document.accepted_clients == natural.manifest.document.accepted_clients
    assert handoff.assignments.height == natural.membership.height

    controlled = construct_population(
        PopulationConstructionRequest(
            PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            nbaiot_canonical_root,
            Seed(1),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            iid_condition(),
        )
    )
    assert len(controlled.manifest.document.accepted_clients) == 20


def test_edge_static_manifest(edge_canonical_root: Path) -> None:
    construction = construct_population(
        PopulationConstructionRequest(
            PopulationId.EDGE_SENSOR_GROUPS,
            edge_canonical_root,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            None,
        )
    )
    assert len(construction.manifest.document.accepted_clients) == 10
