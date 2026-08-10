import nox

nox.options.sessions = ("tests", "format", "lint", "types", "imports")


def install_dev_tools(session: nox.Session) -> None:
    session.install("pytest>=8.0", "pytest-xdist>=3.5", "hypothesis>=6.0")


@nox.session(python=["3.12"])
def tests(session: nox.Session) -> None:

    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q")


@nox.session(python=["3.12"])
def format(session: nox.Session) -> None:

    session.install("ruff>=0.8")
    session.run("ruff", "format", "--check", "src", "tests", "noxfile.py")


@nox.session(python=["3.12"])
def lint(session: nox.Session) -> None:

    session.install("ruff>=0.8", "pylint>=4.0.6")
    session.install(".")
    session.run("ruff", "check", "src", "tests", "noxfile.py")
    session.run("pylint", "src")
    session.run(
        "pylint",
        "--disable=missing-module-docstring,too-few-public-methods,use-implicit-booleaness-not-comparison",
        "tests",
    )


@nox.session(python=["3.12"])
def types(session: nox.Session) -> None:

    session.install("pyright>=1.1.390")
    session.run("pyright")


@nox.session(python=["3.12"])
def imports(session: nox.Session) -> None:

    session.install("import-linter>=2.0")
    session.install(".")
    session.run("lint-imports")
