"""Nothing in this package imports past the plugin surface, and this is what checks it.

``postulo.plugins.api`` is a promise: those names keep working across a minor release, and
a change to one is a deprecation entry before it is a removal. `postulo.plugins.base`,
``postulo.core`` and the rest are this month's internals and may be renamed in a patch
release without a word -- so a plugin that imports them is a plugin that breaks on somebody
else's Tuesday.

It is checked here rather than reviewed by eye because the import that reaches past the
surface is never the one somebody meant to write: it is the one an editor completed. Copy
this file into your own plugin; the only line to change is ``PACKAGE``.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "postulo_helloworld"

#: The one module a plugin may import from Postulo.
SURFACE = "postulo.plugins.api"


def postulo_imports(source: str) -> set[str]:
    """Every ``postulo`` module a file imports, however it spells the import."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            modules = [node.module or ""]
        elif isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        else:
            continue
        found.update(m for m in modules if m == "postulo" or m.startswith("postulo."))
    return found


def test_the_package_imports_only_the_plugin_surface():
    reaching = sorted(
        f"{path.relative_to(PACKAGE.parent).as_posix()} imports {module}"
        for path in PACKAGE.rglob("*.py")
        for module in postulo_imports(path.read_text(encoding="utf-8"))
        if module != SURFACE
    )
    assert reaching == [], f"import these from {SURFACE} instead: {reaching}"


def test_the_check_can_see_an_import_that_reaches_past_the_surface():
    """The check is worth nothing if it cannot fail; this is what proves it looks."""
    assert postulo_imports("from postulo.plugins.base import FieldSpec") == {"postulo.plugins.base"}
    assert postulo_imports("import postulo.core.models as m") == {"postulo.core.models"}
    assert postulo_imports("from . import __version__") == set()
    assert postulo_imports("from postulo_helloworld.source import HOSTS") == set()
