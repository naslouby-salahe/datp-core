"""Authoritative typed dataset and population bindings: resolution, composition, and dispatch."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.core.errors import CapabilityError, ScientificContractError
from datp_core.core.identifiers import (
    DatasetId,
    EvidenceRole,
    PopulationId,
)
from datp_core.data.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.data.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.data.ciciot2023.populations import construct_ciciot_file_clients
from datp_core.data.ciciot2023.schema import CICIOT2023_SCHEMA
from datp_core.data.contracts import CanonicalSchema, MaterializedDataset
from datp_core.data.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.data.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.data.edge_iiotset.populations import construct_edge_sensor_groups, construct_edge_temporal_groups
from datp_core.data.edge_iiotset.schema import EDGE_SCHEMA
from datp_core.data.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.data.nbaiot.materialize import NBaIoTMaterializer
from datp_core.data.nbaiot.populations import construct_nbaiot_dirichlet_clients, construct_nbaiot_natural_devices
from datp_core.data.nbaiot.schema import NBAIOT_SCHEMA
from datp_core.data.populations.contracts import (
    CICIOT_FILE_CLIENTS,
    EDGE_SENSOR_GROUPS,
    EDGE_TEMPORAL_GROUPS,
    NBAIOT_DIRICHLET_CLIENTS,
    NBAIOT_NATURAL_DEVICES,
    ControlledPartitionKind,
    DatasetCapabilities,
    PopulationCapabilities,
    PopulationConstructionRequest,
    PopulationConstructionResult,
    PopulationDeclaration,
    build_population_capabilities,
    population_evidence_role,
)
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT

type DatasetPublication = MaterializedDataset[StrEnum, StrEnum]


@dataclass(frozen=True, slots=True)
class DatasetBinding:
    capabilities: DatasetCapabilities
    schema: CanonicalSchema
    publish: Callable[[Path, Path], DatasetPublication]


def dataset_binding(dataset_id: DatasetId) -> DatasetBinding:
    try:
        return _DATASET_BINDINGS[dataset_id]
    except KeyError as error:
        raise ValueError(f"unsupported dataset identity: {dataset_id}") from error


@dataclass(frozen=True, slots=True)
class PopulationBinding:
    population: PopulationId
    declaration: PopulationDeclaration
    evidentiary_role: EvidenceRole
    capabilities: PopulationCapabilities
    supported_partition_kinds: frozenset[ControlledPartitionKind]
    construct: Callable[[PopulationConstructionRequest], PopulationConstructionResult]


def resolve_population(population_id: PopulationId) -> PopulationBinding:
    matches = tuple(binding for binding in _POPULATION_BINDINGS if binding.population is population_id)
    if len(matches) != 1:
        raise CapabilityError(
            "unsupported population identity",
            subject=population_id,
            reason="population is outside the locked five-population catalogue",
        )
    return matches[0]


def population_declaration(population_id: PopulationId) -> PopulationDeclaration:
    return resolve_population(population_id).declaration


def population_capabilities(population_id: PopulationId) -> PopulationCapabilities:
    return resolve_population(population_id).capabilities


def construct_population(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    binding = resolve_population(request.population_id)
    _require_partition_condition(request, binding)
    return binding.construct(request)


def _require_partition_condition(
    request: PopulationConstructionRequest,
    binding: PopulationBinding,
) -> None:
    condition = request.dirichlet_condition
    if not binding.supported_partition_kinds:
        if condition is not None:
            raise ScientificContractError(
                "population construction does not accept a controlled partition condition",
                subject=request.population_id,
                reason=("only populations with declared controlled partition capability accept one"),
            )
        return
    if condition is None:
        raise ScientificContractError(
            "controlled population construction requires an explicit partition condition",
            subject=request.population_id,
            reason="a controlled partition is never defaulted",
        )
    if condition.kind not in binding.supported_partition_kinds:
        raise ScientificContractError(
            "population construction received an unsupported controlled partition kind",
            subject=request.population_id,
            reason="the partition kind is absent from the population binding",
        )


def _construct_nbaiot_natural(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    return construct_nbaiot_natural_devices(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )


def _construct_nbaiot_dirichlet(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    condition = request.dirichlet_condition
    if condition is None:
        raise AssertionError("partition condition was validated before binding dispatch")
    return construct_nbaiot_dirichlet_clients(
        request.canonical_root,
        partition_seed=request.partition_seed,
        condition=condition,
        split_protocol=request.split_protocol,
        minimum_benign_support=MINIMUM_BENIGN_SUPPORT,
    )


def _construct_ciciot_file_clients_binding(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    return construct_ciciot_file_clients(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )


def _construct_edge_sensor_groups_binding(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    return construct_edge_sensor_groups(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )


def _construct_edge_temporal_groups_binding(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    return construct_edge_temporal_groups(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )


_NBAIOT_PUBLISHER = NBaIoTMaterializer()
_CICIOT2023_PUBLISHER = CICIoT2023Materializer()
_EDGE_IIOTSET_PUBLISHER = EdgeIIoTsetMaterializer()


_DATASET_BINDINGS: dict[DatasetId, DatasetBinding] = {
    DatasetId.NBAIOT: DatasetBinding(NBAIOT_CAPABILITIES, NBAIOT_SCHEMA, _NBAIOT_PUBLISHER.publish),
    DatasetId.CICIOT2023: DatasetBinding(CICIOT2023_CAPABILITIES, CICIOT2023_SCHEMA, _CICIOT2023_PUBLISHER.publish),
    DatasetId.EDGE_IIOTSET: DatasetBinding(EDGE_IIOTSET_CAPABILITIES, EDGE_SCHEMA, _EDGE_IIOTSET_PUBLISHER.publish),
}


_POPULATION_BINDINGS = (
    PopulationBinding(
        PopulationId.NBAIOT_NATURAL_DEVICES,
        NBAIOT_NATURAL_DEVICES,
        population_evidence_role(PopulationId.NBAIOT_NATURAL_DEVICES),
        build_population_capabilities(
            NBAIOT_NATURAL_DEVICES,
            population_evidence_role(PopulationId.NBAIOT_NATURAL_DEVICES),
            NBAIOT_CAPABILITIES,
        ),
        frozenset(),
        _construct_nbaiot_natural,
    ),
    PopulationBinding(
        PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        NBAIOT_DIRICHLET_CLIENTS,
        population_evidence_role(PopulationId.NBAIOT_DIRICHLET_CLIENTS),
        build_population_capabilities(
            NBAIOT_DIRICHLET_CLIENTS,
            population_evidence_role(PopulationId.NBAIOT_DIRICHLET_CLIENTS),
            NBAIOT_CAPABILITIES,
        ),
        frozenset(ControlledPartitionKind),
        _construct_nbaiot_dirichlet,
    ),
    PopulationBinding(
        PopulationId.CICIOT_FILE_CLIENTS,
        CICIOT_FILE_CLIENTS,
        population_evidence_role(PopulationId.CICIOT_FILE_CLIENTS),
        build_population_capabilities(
            CICIOT_FILE_CLIENTS,
            population_evidence_role(PopulationId.CICIOT_FILE_CLIENTS),
            CICIOT2023_CAPABILITIES,
        ),
        frozenset(),
        _construct_ciciot_file_clients_binding,
    ),
    PopulationBinding(
        PopulationId.EDGE_SENSOR_GROUPS,
        EDGE_SENSOR_GROUPS,
        population_evidence_role(PopulationId.EDGE_SENSOR_GROUPS),
        build_population_capabilities(
            EDGE_SENSOR_GROUPS,
            population_evidence_role(PopulationId.EDGE_SENSOR_GROUPS),
            EDGE_IIOTSET_CAPABILITIES,
        ),
        frozenset(),
        _construct_edge_sensor_groups_binding,
    ),
    PopulationBinding(
        PopulationId.EDGE_TEMPORAL_GROUPS,
        EDGE_TEMPORAL_GROUPS,
        population_evidence_role(PopulationId.EDGE_TEMPORAL_GROUPS),
        build_population_capabilities(
            EDGE_TEMPORAL_GROUPS,
            population_evidence_role(PopulationId.EDGE_TEMPORAL_GROUPS),
            EDGE_IIOTSET_CAPABILITIES,
        ),
        frozenset(),
        _construct_edge_temporal_groups_binding,
    ),
)
