from collections.abc import Iterator
from pathlib import Path

from pyarrow import RecordBatch, Schema

class RecordBatchReader:
    def __iter__(self) -> Iterator[RecordBatch]: ...

class Scanner:
    def to_reader(self) -> RecordBatchReader: ...

class Dataset:
    schema: Schema
    def scanner(self, *, batch_size: int, use_threads: bool) -> Scanner: ...

def dataset(source: Path, *, format: str) -> Dataset: ...
