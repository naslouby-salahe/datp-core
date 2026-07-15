from typing import Protocol, Self

import yaml

from datp_core.domain.errors import ConfigurationError


class ValidatedSchema(Protocol):
    @classmethod
    def model_validate(cls, obj: object) -> Self: ...


def load_yaml[Schema: ValidatedSchema](text: str, schema_type: type[Schema]) -> Schema:
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConfigurationError(
            detail="configuration YAML is malformed",
            section="yaml",
            field="document",
            mode="load",
        ) from error
    try:
        return schema_type.model_validate(payload)
    except ValueError as error:
        raise ConfigurationError(
            detail="configuration YAML does not satisfy its declared schema",
            section="yaml",
            field="document",
            mode="load",
        ) from error
