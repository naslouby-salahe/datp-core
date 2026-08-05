"""Public Pydantic adapters for closed DATP-Core domain types."""

from pydantic_core import core_schema


def string_enum_schema(enum_type, _source_type, _handler):
    """Validate one string-backed enum without exposing private value helpers."""

    def validate(value):
        if isinstance(value, enum_type):
            return value
        if not isinstance(value, str):
            raise TypeError(f"expected {enum_type.__name__} or str")
        return enum_type(value)

    return core_schema.no_info_plain_validator_function(validate)
