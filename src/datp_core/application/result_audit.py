"""Application use case for result auditing and completeness verification via a query port."""

from __future__ import annotations

import polars as pl

from datp_core.application.ports import ResultQueryService


class AuditResultsUseCase:
    """Audit result completeness through the injected query port.

    The composition root wires the concrete DuckDB implementation.
    """

    def __init__(self, query_service: ResultQueryService) -> None:
        self._query_service = query_service

    def execute(self, metrics_pattern: str, expected_seeds: int) -> pl.DataFrame:
        return self._query_service.audit_metrics_completeness(metrics_pattern, expected_seeds)


class QueryResultsUseCase:
    """Execute a read-only SQL query through the injected query port.

    The composition root wires the concrete DuckDB implementation.
    """

    def __init__(self, query_service: ResultQueryService) -> None:
        self._query_service = query_service

    def execute(self, sql_query: str) -> pl.DataFrame:
        return self._query_service.execute_query(sql_query)
