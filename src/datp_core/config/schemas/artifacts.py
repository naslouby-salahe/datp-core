from pydantic import BaseModel, ConfigDict

from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    ArtifactRetentionPolicy,
    SerializationFormat,
    WriteDisposition,
)
from datp_core.domain.artifacts.manifests import ArtifactType


class ArtifactSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactSerializationConfig(ArtifactSchema):
    artifact_type: ArtifactType
    serialization_format: SerializationFormat


class ArtifactConfig(ArtifactSchema):
    namespace: ArtifactNamespace
    write_disposition: WriteDisposition
    retention: ArtifactRetentionPolicy
    serialization_defaults: tuple[ArtifactSerializationConfig, ...]
