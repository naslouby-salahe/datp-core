import subprocess
import sys

import nox

nox.options.default_venv_backend = "none"

# Every tool below is invoked as `sys.executable -m <module>` rather than by bare
# command name. Nox's own PATH lookup for `external=True` commands resolves against
# the invoking shell's PATH, which may (and, on this machine, does) contain unrelated
# global installs of ruff/pyright/pytest ahead of this project's `.venv`. Routing
# every call through `sys.executable` pins each session to the exact interpreter and
# environment that invoked Nox, never a coincidental PATH match.
_PYTHON = sys.executable
_NO_TESTS_COLLECTED = 5
_PYTEST_SUCCESS_CODES = (0, _NO_TESTS_COLLECTED)


def _run_pytest(session: nox.Session, *args: str) -> None:
    session.run(_PYTHON, "-m", "pytest", *args, success_codes=_PYTEST_SUCCESS_CODES)


@nox.session
def lint(session: nox.Session) -> None:
    session.run(_PYTHON, "-m", "ruff", "check", ".")


@nox.session
def format(session: nox.Session) -> None:
    session.run(_PYTHON, "-m", "ruff", "format", "--check", ".")


@nox.session
def typecheck(session: nox.Session) -> None:
    session.run(_PYTHON, "-m", "pyright")


@nox.session
def architecture(session: nox.Session) -> None:
    session.run(_PYTHON, "-m", "importlinter.cli", "lint-imports", "--config", "importlinter.ini")
    _run_pytest(session, "tests/architecture", "-m", "architecture", "--no-cov")


@nox.session(name="xdist_safe")
def xdist_safe(session: nox.Session) -> None:
    _run_pytest(session, "-m", "not cuda and not serial and not resource_intensive", "-n", "auto")


@nox.session
def serial(session: nox.Session) -> None:
    _run_pytest(session, "-m", "serial and not cuda")


@nox.session(name="resource_intensive")
def resource_intensive(session: nox.Session) -> None:
    _run_pytest(session, "-m", "resource_intensive")


@nox.session
def cuda(session: nox.Session) -> None:
    _run_pytest(session, "-m", "cuda", "-p", "no:randomly")


@nox.session
def synthetic(session: nox.Session) -> None:
    _run_pytest(session, "tests/system/synthetic", "-m", "system_synthetic")


@nox.session(name="scientific_smoke")
def scientific_smoke(session: nox.Session) -> None:
    _run_pytest(session, "tests/system/scientific_smoke", "-m", "scientific_smoke")


@nox.session
def impacted(session: nox.Session) -> None:
    _run_pytest(session, *session.posargs)


@nox.session
def sonar(session: nox.Session) -> None:
    session.run("sonar", "system", "status", external=True)
    session.run("sonar", "analyze", "--force", external=True)


_CS_UNCONFIGURED_MARKER = "Personal Access Token"


@nox.session
def codescene(session: nox.Session) -> None:
    session.run("cs", "rules-config", "validate", external=True)
    result = subprocess.run(
        ["cs", "delta", "--error-on-warnings"],
        capture_output=True,
        text=True,
        check=False,
    )
    session.log(result.stdout + result.stderr)
    if _CS_UNCONFIGURED_MARKER in result.stdout + result.stderr:
        session.error(
            "CodeScene delta analysis did not actually run: CS_ACCESS_TOKEN is unset, so the "
            "CLI printed its Personal Access Token setup instructions instead of analyzing "
            "anything. Treat this as a blocker, not a pass, regardless of the process exit code "
            "— set CS_ACCESS_TOKEN and rerun this session."
        )
    if result.returncode != 0:
        session.error(f"CodeScene delta analysis reported a code health finding (exit {result.returncode}).")


@nox.session(name="full_suite")
def full_suite(session: nox.Session) -> None:
    session.notify("lint")
    session.notify("format")
    session.notify("typecheck")
    session.notify("architecture")
    session.notify("xdist_safe")
    session.notify("serial")
    session.notify("resource_intensive")
    session.notify("cuda")
    session.notify("synthetic")
    session.notify("scientific_smoke")
    session.notify("sonar")
    session.notify("codescene")
