"""Validated value objects for open data-package domains."""

from __future__ import annotations

from pydantic import ConfigDict, RootModel, field_validator


class NonBlankText(RootModel[str]):
    model_config = ConfigDict(frozen=True, strict=True)

    @field_validator("root")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


class SourceTreeId(NonBlankText):
    pass


class FeatureName(NonBlankText):
    pass


class ColumnName(NonBlankText):
    pass


class SchemaId(NonBlankText):
    pass


class CapabilityId(NonBlankText):
    pass


class AttackFamilyName(NonBlankText):
    pass


class CategoryToken(NonBlankText):
    pass


class LabelValue(NonBlankText):
    pass


class ClientNamePrefix(NonBlankText):
    pass


class GateId(NonBlankText):
    pass
