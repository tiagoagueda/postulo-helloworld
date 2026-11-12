"""Nothing in this package imports past the plugin surface, and this is what checks it.

``postulo.plugins.api`` is a promise: those names keep working across a minor release, and
a change to one is a deprecation entry before it is a removal. `postulo.plugins.base`,
``postulo.core`` and the rest are this month's internals and may be renamed in a patch
release without a word -- so a plugin that imports them is a plugin that breaks on somebody
else's Tuesday.

It is checked rather than reviewed by eye because the import that reaches past the surface
is never the one somebody meant to write: it is the one an editor completed.

**Do not copy this file.** It used to say the opposite -- *"copy this into your own plugin;
the only line to change is PACKAGE"* -- and four plugins did, which is how five
near-identical AST walks ended up in five repositories, no two agreeing about relative
imports or about what counted as reaching past. The core publishes the walk now
(postulo/postulo#229), so the two lines below are the whole of what a plugin needs:
``assert_imports_only_the_surface`` over your package, and the names you ask of the surface
asserted against ``api.__all__``. This is the plugin people are told to copy, so what it
shows should be the check the core maintains rather than a snapshot of it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from postulo.plugins.testing import SURFACE, assert_imports_only_the_surface, imports_of

PACKAGE = "postulo_helloworld"
SOURCE = Path(__file__).resolve().parents[1] / "src" / PACKAGE


def test_there_is_something_to_check():
    """A sanity check on the check: an empty package would make everything below pass."""
    assert len(list(SOURCE.rglob("*.py"))) >= 2


def test_the_package_imports_only_the_plugin_surface():
    assert_imports_only_the_surface(SOURCE, package=PACKAGE)


def test_the_surface_is_what_this_plugin_actually_uses():
    """The other half: the surface is imported, rather than merely not reached past."""
    found = imports_of(SOURCE, package=PACKAGE)
    assert found, "the package imports nothing from Postulo"
    # By name since postulo/postulo 12504e44f: `postulo.plugins.api.FieldSpec`, not the module.
    assert all(name == SURFACE or name.startswith(SURFACE + ".") for name in found), found


@pytest.mark.parametrize("name", ["FieldSpec", "JobPostingData", "TestResult"])
def test_the_surface_promises_what_this_plugin_asks_of_it(name: str):
    """Not merely importable: on ``__all__``, which is what the promise is made about.

    A name that resolves today because it happens to be reachable is not a name that keeps
    working across a release. Three names is the whole of what the smallest plugin needs.
    """
    from postulo.plugins import api

    assert name in api.__all__, f"{SURFACE} does not promise {name}"


def test_the_readme_names_nothing_past_the_surface_to_import_or_call():
    """#10: the README told authors to call ``postulo.plugins.http.client()``, which the
    check above refuses. Every Postulo module it names has to be the surface or the test
    helpers; a dotted name that is no module at all (an entry-point group) is not one."""
    import importlib.util
    import re

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    past = set()
    for name in set(re.findall(r"\bpostulo(?:\.\w+)+", readme)):
        parts = name.split(".")
        modules = []
        for end in range(2, len(parts) + 1):
            try:
                if importlib.util.find_spec(".".join(parts[:end])) is not None:
                    modules.append(".".join(parts[:end]))
            except ModuleNotFoundError:
                break
        if modules and modules[-1] not in (SURFACE, "postulo.plugins.testing"):
            past.add(name)
    assert not past, f"the README names modules past the plugin surface: {sorted(past)}"
