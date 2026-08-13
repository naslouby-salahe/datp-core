import nox

nox.options.sessions = ("tests", "format", "lint", "types", "imports")
nox.options.reuse_existing_virtualenvs = True


def install_dev_tools(session: nox.Session, *, pylint: bool = False) -> None:
    tools = ["pytest>=8.0", "pytest-xdist>=3.5", "hypothesis>=6.0"]
    if pylint:
        tools.extend(["pylint>=4.0.6", "import-linter>=2.0"])
    session.install(*tools)


@nox.session(python=["3.12"])
def tests(session: nox.Session) -> None:
    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q")


@nox.session(python=["3.12"])
def unit(session: nox.Session) -> None:
    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q", "tests/unit")


@nox.session(python=["3.12"])
def integration(session: nox.Session) -> None:
    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q", "tests/integration")


@nox.session(python=["3.12"])
def property(session: nox.Session) -> None:
    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q", "tests/property")


@nox.session(python=["3.12"])
def scientific(session: nox.Session) -> None:
    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q", "tests/scientific")


@nox.session(python=["3.12"])
def e2e(session: nox.Session) -> None:
    install_dev_tools(session)
    session.install(".")
    session.run("python", "-m", "pytest", "-n", "auto", "-q", "tests/e2e")


@nox.session(python=["3.12"])
def format(session: nox.Session) -> None:
    session.install("ruff>=0.8")
    session.run("ruff", "format", "--check", "src", "tests", "tools", "noxfile.py")


@nox.session(python=["3.12"])
def lint(session: nox.Session) -> None:
    install_dev_tools(session, pylint=True)
    session.install(".")
    session.run("ruff", "check", "src", "tests", "tools", "noxfile.py")
    session.run("pylint", "src")
    session.run(
        "pylint",
        "--disable=missing-module-docstring,too-few-public-methods,use-implicit-booleaness-not-comparison",
        "tests",
    )
    session.run("lint-imports")


@nox.session(python=["3.12"])
def types(session: nox.Session) -> None:
    session.install("pyright>=1.1.390")
    session.run("pyright")


@nox.session(python=["3.12"])
def imports(session: nox.Session) -> None:
    session.install("import-linter>=2.0")
    session.install(".")
    session.run("lint-imports")
