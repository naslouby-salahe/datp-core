from pathlib import Path

from pyarrow import Schema, Table

class FileMetaData:
    num_rows: int

class ParquetFile:
    metadata: FileMetaData
    schema_arrow: Schema
    def __init__(self, where: Path) -> None: ...

class ParquetWriter:
    def __init__(self, where: Path, schema: Schema, *, compression: str | None = ...) -> None: ...
    def __enter__(self) -> ParquetWriter: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...
    def write_table(self, table: Table) -> None: ...
