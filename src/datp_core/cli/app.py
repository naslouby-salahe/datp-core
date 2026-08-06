"""Root Typer application composed from focused command families."""

import typer

from datp_core.cli.anchor import app as anchor_app
from datp_core.cli.execution import app as execution_app
from datp_core.cli.inspect import app as inspect_app
from datp_core.cli.plan import app as plan_app

app = typer.Typer(no_args_is_help=True, help="Reproducible DATP-Core operations.")
app.add_typer(plan_app, name="plan")
app.add_typer(execution_app, name="run")
app.add_typer(inspect_app, name="inspect")
app.add_typer(anchor_app, name="anchor")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
