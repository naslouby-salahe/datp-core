"""Strict persisted documents for federated checkpoint inventories."""

from pydantic import model_validator

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    ClientPathToken,
    PopulationId,
    PreprocessingProtocolId,
    SafeTensorFilename,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    BatchSize,
    DirichletConcentration,
    ManifestSchemaVersion,
    ModelCoefficientValue,
    RoundNumber,
    Seed,
)
from datp_core.data.populations.contracts import ControlledPartitionKind
from datp_core.detector.checkpoints.identities import CandidateManifestKind
from datp_core.detector.training.contracts import AutoencoderArchitecture


class CandidateManifestEntry(StrictModel):
    round_number: RoundNumber
    client_id: ClientPathToken | None
    tensor_name: SafeTensorFilename
    tensor_checksum: Checksum


class CandidateManifest(StrictModel):
    schema_version: ManifestSchemaVersion
    kind: CandidateManifestKind
    coordinate_population: PopulationId
    coordinate_training_seed: Seed
    coordinate_split_protocol: SplitProtocolId
    coordinate_preprocessing_identity: PreprocessingProtocolId
    coordinate_model: TrainingModelId
    coordinate_model_coefficient: ModelCoefficientValue | None
    coordinate_controlled_partition_kind: ControlledPartitionKind | None
    coordinate_dirichlet_concentration: DirichletConcentration | None
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    checkpoint_rounds: tuple[RoundNumber, ...]
    autoencoder_widths: AutoencoderArchitecture
    batch_size: BatchSize
    linked_personalized_digest: Checksum | None
    entries: tuple[CandidateManifestEntry, ...]

    @model_validator(mode="after")
    def validate_controlled_partition_coordinate(self) -> "CandidateManifest":
        if self.coordinate_controlled_partition_kind is None and self.coordinate_dirichlet_concentration is not None:
            raise ValueError("a Dirichlet concentration requires a controlled partition kind")
        if (
            self.coordinate_controlled_partition_kind is ControlledPartitionKind.IID
            and self.coordinate_dirichlet_concentration is not None
        ):
            raise ValueError("IID controlled partitions must not carry a concentration")
        if (
            self.coordinate_controlled_partition_kind is ControlledPartitionKind.DIRICHLET
            and self.coordinate_dirichlet_concentration is None
        ):
            raise ValueError("Dirichlet controlled partitions require a concentration")
        return self
