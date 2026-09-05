"""postulo-helloworld: the smallest Postulo plugin, to be copied.

Two plugins live here, one of each kind Postulo has today:

- :class:`~postulo_helloworld.source.HelloWorldSource` is a **capture source**. It reads
  a posting out of a page and hands Postulo the data; Postulo shows it for review.
- :class:`~postulo_helloworld.notifier.HelloWorldNotifier` is a **notifier**, a connected
  plugin. A person adds a connection to it under Settings, chooses which events reach it,
  and it writes each one to a file.

Every string a person reads is translated by this package itself, from ``locale/`` next to
this file; Postulo never carries a plugin's words. Everything is registered through entry
points in ``pyproject.toml``, so installing the package into Postulo's environment is the
whole installation.
"""

__version__ = "0.1.0"
