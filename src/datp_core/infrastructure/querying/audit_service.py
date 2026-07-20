"""DuckDB in-memory read-only SQL query and result auditing service."""

from __future__ import annotations

import duckdb
import polars as pl

from datp_core.config.resolver import ResolvedProjectConfiguration

SqlParameter = str | int | float | bool | None


class DuckDbAuditService:
    """Read-only SQL audit service over Parquet result artifacts using DuckDB."""

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config
        self._outputs_dir = self._config.paths.outputs

    def execute_query(self, sql_query: str, params: tuple[SqlParameter, ...] = ()) -> pl.DataFrame:
        con = duckdb.connect(database=":memory:")
        try:
            rel = con.execute(sql_query, params)
            arrow_table = rel.fetch_arrow_table()
            return pl.from_arrow(arrow_table)  # type: ignore
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
