"""postulo-helloworld: the smallest Postulo plugin, to be copied.

Two plugins live here, one of each kind Postulo has today:

- :class:`~postulo_helloworld.source.HelloWorldSource` is a **capture source**. It reads
  a posting out of a page and hands Postulo the data; Postulo shows it for review.
- :class:`~postulo_helloworld.notifier.HelloWorldNotifier` is a **notifier**, a connected
  plugin. A person adds a connection to it under Settings, chooses which events reach it,
  and it writes each one to a file the operator's directory holds.

Both import from ``postulo.plugins.api`` and from nothing else in Postulo. That module is
the promise; everything else is internals, and ``tests/test_surface.py`` here fails on an
import that reaches past it.

Every string a person reads is translated by this package itself, from ``locale/`` next to
this file; Postulo never carries a plugin's words. Everything is registered through entry
points in ``pyproject.toml``, so installing the package into Postulo's environment is the
whole installation.
"""

from importlib.metadata import version

#: Read from the installed distribution, so ``pyproject.toml`` is the only place a version
#: is written. It is recorded against every capture this source made and every connection
#: the notifier holds, and two numbers that can disagree eventually do. Installing the
#: package is how a plugin becomes loadable at all, so the metadata is always there.
__version__ = version("postulo-helloworld")
