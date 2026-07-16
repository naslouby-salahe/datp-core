from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Self, cast

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from datp_core.config.documents import ConfigurationDocument, configuration_document_path
from datp_core.domain.errors import ConfigurationError


class ValidatedSchema(Protocol):
    @classmethod
    def model_validate(cls, obj: object) -> Self: ...


def parse_yaml_mapping(*, text: str, document: ConfigurationDocument) -> Mapping[str, object]:
    root = _parse_yaml_root(text=text, document=document)
    _validate_yaml_node(root=root, document=document)
    return _load_mapping(text=text, document=document)


def _parse_yaml_root(*, text: str, document: ConfigurationDocument) -> MappingNode:
    _reject_yaml_aliases(text=text, document=document)
    node = cast(
        Node | None,
        _yaml_operation(
            operation=lambda: _compose_yaml(text=text),
            document=document,
        ),
    )
    if not isinstance(node, MappingNode):
        raise ConfigurationError(
            detail="configuration document root must be a mapping",
            section="loader",
            field=document.value,
            mode="load",
        )
    return node


def _reject_yaml_aliases(*, text: str, document: ConfigurationDocument) -> None:
    events = cast(
        tuple[object, ...],
        _yaml_operation(
            operation=lambda: _parse_yaml_events(text=text),
            document=document,
        ),
    )
    if any(isinstance(event, AliasEvent) for event in events):
        raise ConfigurationError(
            detail="configuration YAML must not use aliases or implicit inheritance",
            section="loader",
            field=document.value,
            mode="load",
        )


def _load_mapping(*, text: str, document: ConfigurationDocument) -> Mapping[str, object]:
    payload = _yaml_operation(
        operation=lambda: _safe_load_yaml(text=text),
        document=document,
    )
    if not isinstance(payload, Mapping):
        raise ConfigurationError(
            detail="configuration document root must be a mapping",
            section="loader",
            field=document.value,
            mode="load",
        )
    return cast(Mapping[str, object], payload)


def _compose_yaml(*, text: str) -> Node | None:
    return cast(Node | None, yaml.compose(text, Loader=yaml.SafeLoader))  # pyright: ignore[reportUnknownMemberType]


def _parse_yaml_events(*, text: str) -> tuple[object, ...]:
    return cast(
        tuple[object, ...],
        tuple(yaml.parse(text, Loader=yaml.SafeLoader)),  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
    )


def _safe_load_yaml(*, text: str) -> object:
    return cast(object, yaml.safe_load(text))  # pyright: ignore[reportUnknownMemberType]


def _yaml_operation(*, operation: Callable[[], object], document: ConfigurationDocument) -> object:
    try:
        return operation()
    except yaml.YAMLError as error:
        raise ConfigurationError(
            detail="configuration YAML is malformed",
            section="loader",
            field=document.value,
            mode="load",
        ) from error


def load_yaml_document[Schema: ValidatedSchema](
    *, text: str, schema_type: type[Schema], document: ConfigurationDocument
) -> Schema:
    try:
        return schema_type.model_validate(parse_yaml_mapping(text=text, document=document))
    except ValueError as error:
        raise ConfigurationError(
            detail="configuration YAML does not satisfy its declared schema",
            section="loader",
            field=document.value,
            mode="validation",
        ) from error


def _validate_yaml_node(*, root: Node, document: ConfigurationDocument) -> None:
    match root:
        case MappingNode(value=values):
            keys: set[str] = set()
            for key, value in values:
                _validate_mapping_key(key=key, keys=keys, document=document)
                _validate_yaml_node(root=value, document=document)
        case SequenceNode(value=values):
            for value in values:
                _validate_yaml_node(root=value, document=document)
        case ScalarNode(tag="tag:yaml.org,2002:null"):
            raise ConfigurationError(
                detail="configuration YAML must not contain null values",
                section="loader",
                field=document.value,
                mode="validation",
            )
        case ScalarNode():
            return
        case _:
            raise ConfigurationError(
                detail="configuration YAML contains an unsupported node",
                section="loader",
                field=document.value,
                mode="validation",
            )


def _validate_mapping_key(*, key: Node, keys: set[str], document: ConfigurationDocument) -> None:
    if not isinstance(key, ScalarNode):
        raise ConfigurationError(
            detail="configuration YAML must use non-null scalar keys and cannot use merge keys",
            section="loader",
            field=document.value,
            mode="validation",
        )
    _validate_scalar_mapping_key(key=key, document=document)
    if key.value in keys:
        raise ConfigurationError(
            detail="configuration YAML must not contain duplicate keys",
            section="loader",
            field=document.value,
            mode="validation",
        )
    keys.add(key.value)


def _validate_scalar_mapping_key(*, key: ScalarNode, document: ConfigurationDocument) -> None:
    if key.tag != "tag:yaml.org,2002:null" and key.value != "<<":
        return
    raise ConfigurationError(
        detail="configuration YAML must use non-null scalar keys and cannot use merge keys",
        section="loader",
        field=document.value,
        mode="validation",
    )


@dataclass(slots=True, kw_only=True)
class ConfigurationDocumentLoader:
    root: Path
    _contents: dict[ConfigurationDocument, str] = field(default_factory=lambda: {}, init=False)

    def load[Schema: ValidatedSchema](self, *, document: ConfigurationDocument, schema_type: type[Schema]) -> Schema:
        text = self._read_once(document=document)
        return load_yaml_document(text=text, schema_type=schema_type, document=document)

    def raw_content(self, *, document: ConfigurationDocument) -> str:
        return self._read_once(document=document)

    def _read_once(self, *, document: ConfigurationDocument) -> str:
        if document not in self._contents:
            path = configuration_document_path(root=self.root, document=document)
            try:
                self._contents[document] = path.read_text(encoding="utf-8")
            except FileNotFoundError as error:
                raise ConfigurationError(
                    detail="required configuration document is missing",
                    section="loader",
                    field=document.value,
                    mode="load",
                ) from error
        return self._contents[document]
