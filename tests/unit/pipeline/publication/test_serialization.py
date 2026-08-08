from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.artifacts.repositories.publication import load_model_file, serialize_json_model


class ExampleDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identity: str
    ordinal: int


def test_canonical_json_round_trip_is_atomic_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    destination = tmp_path / "manifest.json"
    document = ExampleDocument(identity="experiment", ordinal=1)

    checksum = serialize_json_model(document, destination)

    assert checksum.value
    assert load_model_file(ExampleDocument, destination) == document
    assert tuple(tmp_path.glob(".manifest.json.*.tmp")) == ()


def test_replacement_never_leaves_previous_document_visible(tmp_path: Path) -> None:
    destination = tmp_path / "manifest.json"
    first = ExampleDocument(identity="first", ordinal=1)
    second = ExampleDocument(identity="second", ordinal=2)

    serialize_json_model(first, destination)
    serialize_json_model(second, destination)

    assert load_model_file(ExampleDocument, destination) == second
    assert tuple(tmp_path.iterdir()) == (destination,)
