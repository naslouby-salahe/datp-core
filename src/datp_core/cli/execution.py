"""Composition root for execution command families."""

import typer

from datp_core.cli.confirmatory import app as confirmatory_app
from datp_core.cli.datasets import app as datasets_app
from datp_core.cli.external import app as external_app
from datp_core.cli.personalization import app as personalization_app
from datp_core.cli.temporal import app as temporal_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(datasets_app)
app.add_typer(confirmatory_app)
app.add_typer(personalization_app)
app.add_typer(external_app)
app.add_typer(temporal_app)
