"""Validated path and identity components."""

from dataclasses import dataclass

from datp_core.domain.values.base import pydantic_value_schema


@dataclass(frozen=True, slots=True)
class ClientPathToken:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("client path token must be non-empty")
        if self.value in {".", ".."} or any(token in self.value for token in ("=", "/", "\\")):
            raise ValueError("client path token must be a single non-relative path segment without key=value syntax")

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


@dataclass(frozen=True, slots=True)
class FamilyIdentity:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("family identity must be non-empty")

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)
