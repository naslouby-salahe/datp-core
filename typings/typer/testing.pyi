from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typer import Typer

class Result:
    exit_code: int
    stdout: str

class CliRunner:
    def invoke(self, app: Typer, args: list[str] | None = ...) -> Result: ...
