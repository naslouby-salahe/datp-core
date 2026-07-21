"""Query use cases operate through a fake ResultQueryService port."""

from __future__ import annotations

import polars as pl

from datp_core.application.result_audit import AuditResultsUseCase, QueryResultsUseCase


class FakeQueryService:
    """Fake ResultQueryService that records calls and returns canned data."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.audit_calls: list[tuple[str, int]] = []

    def execute_query(self, sql_query: str) -> pl.DataFrame:
        self.queries.append(sql_query)
        return pl.DataFrame({"result": [1]})

    def audit_metrics_completeness(self, metrics_parquet_pattern: str, expected_seed_count: int) -> pl.DataFrame:
        self.audit_calls.append((metrics_parquet_pattern, expected_seed_count))
        return pl.DataFrame({"policy_id": ["test"], "distinct_seed_count": [expected_seed_count], "total_rows": [100]})


def test_query_results_use_case_delegates_to_port() -> None:
    """QueryResultsUseCase must delegate execute() to the injected port."""
    fake = FakeQueryService()
    use_case = QueryResultsUseCase(fake)

    result = use_case.execute("SELECT 1")

    assert fake.queries == ["SELECT 1"]
    assert result["result"][0] == 1


def test_audit_results_use_case_delegates_to_port() -> None:
    """AuditResultsUseCase must delegate execute() to the injected port."""
    fake = FakeQueryService()
    use_case = AuditResultsUseCase(fake)

    result = use_case.execute("metrics/*.parquet", 10)

    assert fake.audit_calls == [("metrics/*.parquet", 10)]
    assert result["distinct_seed_count"][0] == 10


def test_query_results_use_case_does_not_import_duckdb() -> None:
    """QueryResultsUseCase must not import DuckDbAuditService."""
    import ast
    from pathlib import Path

    source = (Path(__file__).parents[3] / "src" / "datp_core" / "application" / "result_audit.py").read_text()
    tree = ast.parse(source)
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None]
    assert "datp_core.infrastructure.querying.audit_service" not in imports, (
        "result_audit.py must not import DuckDbAuditService"
    )
