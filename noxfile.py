"""Repeatable local and CI quality gates for DATP Core."""

import nox

nox.options.sessions = ("lint", "typecheck", "tests_full", "imports", "scientific_invariants")


@nox.session(venv_backend="uv")
def format(session: nox.Session) -> None:
    """Format source code with Ruff."""
    session.install("ruff>=0.8")
    session.run("ruff", "format", "src", "tests")
    session.run("ruff", "check", "--fix", "src", "tests")


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
def pylint(session: nox.Session) -> None:
    """Run Pylint static analysis over production code."""
    session.install(".", "pylint>=3.0")
    session.run("pylint", "src/datp_core")


@nox.session(venv_backend="uv")
def tests(session: nox.Session) -> None:
    """Run the test suite in parallel, including Hypothesis and benchmark tests."""
    session.install(".[cli]", "pytest>=8.0", "hypothesis>=6.0", "pytest-benchmark>=4.0", "pytest-xdist>=3.5")
    session.run("pytest", "-q", "-n", "auto")


@nox.session(venv_backend="uv")
def tests_full(session: nox.Session) -> None:
    """Run the full test suite with coverage for SonarQube."""
    session.install(
        ".[cli]",
        "pytest>=8.0",
        "hypothesis>=6.0",
        "pytest-benchmark>=4.0",
        "pytest-cov>=5.0",
    )
    session.run(
        "pytest",
        "-q",
        "--cov=src/datp_core",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term",
    )


@nox.session(venv_backend="uv")
def imports(session: nox.Session) -> None:
    """Enforce the layer dependency contracts."""
    session.install(".", "import-linter>=2.0")
    session.run("lint-imports", "--config", "importlinter.ini")


@nox.session(venv_backend="uv")
def contracts(session: nox.Session) -> None:
    """Run contract and scientific invariant tests."""
    session.install(".[cli]", "pytest>=8.0", "hypothesis>=6.0")
    session.run("pytest", "-q", "tests/scientific/", "tests/integration/")


@nox.session(venv_backend="uv")
def scientific_invariants(session: nox.Session) -> None:
    """Run scientific invariant tests only."""
    session.install(".[cli]", "pytest>=8.0", "hypothesis>=6.0")
    session.run("pytest", "-q", "tests/scientific/")


@nox.session(venv_backend="uv")
def smoke_synthetic(session: nox.Session) -> None:
    """Run synthetic end-to-end pipeline smoke tests."""
    session.install(".[cli]", "pytest>=8.0")
    session.run("pytest", "-q", "-m", "smoke", "tests/")


@nox.session(venv_backend="uv")
def smoke_experiments(session: nox.Session) -> None:
    """Launch time-boxed real-data experiment smokes (requires GPU)."""
    session.install(".[cli]")
    session.run("datp-core", "smoke", "--profile", "smoke")


@nox.session(venv_backend="uv")
def sonar(session: nox.Session) -> None:
    """Run SonarQube analysis via sonar-scanner."""
    session.run("sonar-scanner", external=True)


@nox.session(venv_backend="uv")
def quality(session: nox.Session) -> None:
    """Run all quality gates: lint, typecheck, pylint, tests, imports, scientific invariants, smoke synthetic."""
    session.notify("lint")
    session.notify("typecheck")
    session.notify("pylint")
    session.notify("tests_full")
    session.notify("imports")
    session.notify("scientific_invariants")
    session.notify("smoke_synthetic")
