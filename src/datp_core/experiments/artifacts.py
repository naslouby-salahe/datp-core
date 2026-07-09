"""Generic JSON artifact writing shared by every anchor pipeline stage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any


def write_json_document(document: Mapping[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True))


def write_manifest(manifest: Any, path: Path) -> None:
    write_json_document(asdict(manifest), path)
