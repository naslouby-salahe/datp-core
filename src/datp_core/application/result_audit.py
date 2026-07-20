"""Application use case for result auditing and completeness verification via DuckDB."""

from __future__ import annotations

import polars as pl

from datp_core.infrastructure.querying.audit_service import DuckDbAuditService


class AuditResultsUseCase:
    def __init__(self, duckdb_service: DuckDbAuditService) -> None:
        self._duckdb_service = duckdb_service

    def execute(self, metrics_pattern: str, expected_seeds: int) -> pl.DataFrame:
        return self._duckdb_service.audit_metrics_completeness(metrics_pattern, expected_seeds)


class QueryResultsUseCase:
    def __init__(self, duckdb_service: DuckDbAuditService) -> None:
        self._duckdb_service = duckdb_service

    def execute(self, sql_query: str) -> pl.DataFrame:
        return self._duckdb_service.execute_query(sql_query)
