from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, revalidate_instances="never")


def pydantic_value_schema(cls, _source_type, _handler):

    def validate(value):
        return value if isinstance(value, cls) else cls(value)

    return core_schema.no_info_plain_validator_function(
        validate,
        serialization=core_schema.plain_serializer_function_ser_schema(lambda instance: instance.value),
    )


def str_subclass_schema(cls: type, _source_type: object, _handler: object) -> object:

    def validate(value: object) -> object:
        return value if isinstance(value, cls) else cls(value)

    return core_schema.no_info_plain_validator_function(
        validate,
        serialization=core_schema.plain_serializer_function_ser_schema(str),
    )


def str_enum_schema[EnumT: StrEnum](
    cls: type[EnumT], _source_type: object, _handler: GetCoreSchemaHandler
) -> CoreSchema:

    def validate(value: object) -> EnumT:
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"expected {cls.__name__} or str")
        return cls(value)

    return core_schema.no_info_plain_validator_function(validate)


def sequence_pydantic_schema(cls: type, _source_type: object, _handler: GetCoreSchemaHandler) -> CoreSchema:

    def validate(value: object) -> object:
        if isinstance(value, cls):
            return value
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return cls(tuple(value))
        raise ValueError(f"expected sequence, got {type(value)}")

    def scalar_values(instance: object) -> list[object]:
        if not isinstance(instance, Iterable) or isinstance(instance, (str, bytes)):
            raise TypeError("typed sequence serialization requires an iterable")
        return [getattr(item, "value", item) for item in instance]

    return core_schema.no_info_plain_validator_function(
        validate,
        serialization=core_schema.plain_serializer_function_ser_schema(scalar_values),
    )


def validate_non_empty_tuple(values: tuple[object, ...], field_name: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field_name} requires a non-empty tuple")


def validate_unique(values: tuple[object, ...], field_name: str) -> None:
    if len(frozenset(values)) != len(values):
        raise ValueError(f"{field_name} must be unique")


@dataclass(frozen=True, slots=True)
class ClientOwned[ClientT, ValueT]:
    client: ClientT
    value: ValueT


@dataclass(frozen=True, slots=True)
class ClientCollection[ClientT, ValueT]:
    items: tuple[ClientOwned[ClientT, ValueT], ...]

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("client collection cannot be empty")
        clients = tuple(item.client for item in self.items)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("client collection cannot contain duplicate owners")

    def require(self, client: ClientT) -> ValueT:
        matches = tuple(item.value for item in self.items if item.client == client)
        if len(matches) != 1:
            raise KeyError(f"expected exactly one value for client {client}")
        return matches[0]

    def clients(self) -> tuple[ClientT, ...]:
        return tuple(item.client for item in self.items)

    def values(self) -> tuple[ValueT, ...]:
        return tuple(item.value for item in self.items)
