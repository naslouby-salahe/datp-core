"""Authored configuration schema entry point, re-exporting base model classes shared across every
authored document family."""

from datp_core.config.authored.base import SchemaVersionOneConfigModel, StrictFrozenConfigModel

__all__ = ["SchemaVersionOneConfigModel", "StrictFrozenConfigModel"]
