from dataclasses import dataclass

import msgspec
from torch import Tensor

from datp_core.application.ports.learning import TrainCentralizedModelRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash

_CHECKPOINT_SCHEMA_VERSION = ArtifactSchemaVersion(value="v1")


def _content_and_hash(parameters: tuple[Tensor, ...]) -> tuple[bytes, str]:
    flattened: list[list[float]] = [parameter.detach().cpu().flatten().tolist() for parameter in parameters]  # type: ignore[reportUnknownMemberType]  # PyTorch's stub omits the element type.
    content = msgspec.json.encode(tuple(tuple(values) for values in flattened))
    return content, blake3_bytes_content_hash(content)


@dataclass(frozen=True, slots=True, kw_only=True)
class B0CentralizedCheckpointStager:
    parameters: tuple[Tensor, ...]

    def stage(self, request: TrainCentralizedModelRequest) -> ArtifactRef:
        if type(request.comparator) is not CentralizedModelComparatorSpec:
            raise DomainValidationError(
                detail="B0 checkpoint staging requires a centralized comparator identity, never a FedAvg identity",
                value=repr(request.comparator),
                constraint="CentralizedModelComparatorSpec",
            )
        if not self.parameters:
            raise DomainValidationError(
                detail="B0 checkpoint staging requires at least one trained parameter tensor",
                value=repr(self.parameters),
                constraint="non-empty tuple[Tensor, ...]",
            )
        _, content_hash = _content_and_hash(self.parameters)
        return ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + content_hash),
            artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT,
            content_hash=content_hash,
            schema_version=_CHECKPOINT_SCHEMA_VERSION,
            serialization_format=SerializationFormat.TORCH_STATE,
        )
