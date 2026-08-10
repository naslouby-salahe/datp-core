from importlib import import_module
from pkgutil import walk_packages

import datp_core


def test_every_datp_core_module_imports() -> None:
    failures: list[str] = []
    module_names = tuple(
        sorted(module.name for module in walk_packages(datp_core.__path__, prefix=f"{datp_core.__name__}."))
    )
    for module_name in module_names:
        try:
            import_module(module_name)
        except Exception as error:
            failures.append(f"{module_name}: {type(error).__name__}: {error}")
    assert not failures, "package import failures:\n" + "\n".join(failures)
