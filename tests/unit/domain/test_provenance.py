from pathlib import Path

from datp_core.domain.enums import DatasetId
from datp_core.domain.provenance import DatasetProvenance, SourceFileProvenance
from datp_core.domain.values import ByteCount, Checksum


def test_provenance_is_typed_and_immutable() -> None:
    source = SourceFileProvenance(Path("data/a"), ByteCount(1), Checksum("AB"), 1)
    assert DatasetProvenance(DatasetId.NBAIOT, (source,), Checksum("CD")).sources == (source,)
