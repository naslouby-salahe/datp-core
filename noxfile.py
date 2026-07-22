"""Repeatable local and CI quality gates for DATP Core."""

import nox

nox.options.sessions = ("lint", "typecheck", "tests", "tests_parallel", "imports", "coverage")


@nox.session(venv_backend="uv")
def lint(session: nox.Session) -> None:
    """Check formatting and linting without modifying the source tree."""
    session.install(".", "ruff>=0.8")
    session.run("ruff", "format", "--check", "src", "tests")
    session.run("ruff", "check", "src", "tests")


@nox.session(venv_backend="uv")
def typecheck(session: nox.Session) -> None:
    """Run static type checks over production and test code."""
    session.install(".", "pyright>=1.1.390")
    session.run("pyright")


@nox.session(venv_backend="uv")
def tests(session: nox.Session) -> None:
    """Run the serial test suite, including Hypothesis and benchmark tests."""
    session.install(".[cli]", "pytest>=8.0", "hypothesis>=6.0", "pytest-benchmark>=4.0")
    session.run("pytest", "-q")


@nox.session(venv_backend="uv")
def tests_parallel(session: nox.Session) -> None:
    """Run the suite under xdist to expose shared-state defects."""
    session.install(".[cli]", "pytest>=8.0", "hypothesis>=6.0", "pytest-benchmark>=4.0", "pytest-xdist>=3.5")
    session.run("pytest", "-q", "-n", "auto")


@nox.session(venv_backend="uv")
def imports(session: nox.Session) -> None:
    """Enforce the layer dependency contracts."""
    session.install(".", "import-linter>=2.0")
    session.run("lint-imports", "--config", "importlinter.ini")


@nox.session(venv_backend="uv")
def coverage(session: nox.Session) -> None:
    """Run tests with coverage and produce coverage.xml for SonarQube."""
    session.install(".[cli]", "pytest>=8.0", "hypothesis>=6.0", "pytest-benchmark>=4.0", "pytest-cov>=5.0")
    session.run(
        "pytest", "-q",
        "--cov=src/datp_core",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term",
    )
