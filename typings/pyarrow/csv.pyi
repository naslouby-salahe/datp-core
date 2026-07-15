from collections.abc import Iterator
from pathlib import Path

from pyarrow import RecordBatch, Schema

class ReadOptions:
    def __init__(self, *, block_size: int = ...) -> None: ...

class CSVStreamingReader:
    schema: Schema
    def __iter__(self) -> Iterator[RecordBatch]: ...

def open_csv(input_file: Path, *, read_options: ReadOptions = ...) -> CSVStreamingReader: ...
