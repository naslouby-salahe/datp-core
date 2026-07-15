from datp_core.config.schemas.artifacts import ArtifactConfig
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.experiments.protocols import ArtifactPolicy
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry


def map_artifact_config(schema: ArtifactConfig) -> ArtifactPolicy:
    entries = tuple(
        EnumMapEntry(key=item.artifact_type, value=item.serialization_format) for item in schema.serialization_defaults
    )
    return ArtifactPolicy(
        namespace=schema.namespace,
        write_disposition=schema.write_disposition,
        serialization_defaults=EnumMap(entries=entries, allowed_keys=tuple(ArtifactType), is_sparse=False),
        retention=schema.retention,
    )
