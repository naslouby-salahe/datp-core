"""DuckDB in-memory read-only SQL query and result auditing service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import polars as pl


class DuckDbAuditService:
    """Read-only SQL audit service over Parquet result artifacts using DuckDB."""

    def __init__(self, outputs_dir: Path = Path("outputs")) -> None:
        self._outputs_dir = outputs_dir

    def execute_query(self, sql_query: str, params: tuple[Any, ...] = ()) -> pl.DataFrame:
        con = duckdb.connect(database=":memory:")
        try:
            rel = con.execute(sql_query, params)
            arrow_table = rel.fetch_arrow_table()
            return pl.from_arrow(arrow_table) # type: ignore
        finally:
            con.close()

    def audit_metrics_completeness(self, metrics_parquet_pattern: str, expected_seed_count: int) -> pl.DataFrame:
        sql = """
        SELECT
            policy_id,
            COUNT(DISTINCT seed) as distinct_seed_count,
            COUNT(*) as total_rows
        FROM read_parquet(?)
        GROUP BY policy_id
        HAVING distinct_seed_count < ?
        """
        pattern_path = str(self._outputs_dir / metrics_parquet_pattern)
        return self.execute_query(sql, (pattern_path, expected_seed_count))
