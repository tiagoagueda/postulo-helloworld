"""A notifier: a connected plugin that carries a message somewhere.

A connected plugin describes what it needs from a person as a list of fields, and Postulo
draws the connection form, stores secrets encrypted, offers a *Test* button, and adds a
switch per event. The plugin never renders HTML and never asks which events to deliver: if
``send()`` is called, the person wanted it.

This one appends each notification to a file, which is the simplest thing that can be seen
to work. The person names the file; **where** it is written is the operator's to decide and
not theirs -- see :func:`file_for`, which is the part of this module worth copying. A real
notifier would call a service through ``postulo.plugins.api.client()``, which carries
Postulo's timeouts, user agent and destination policy.

Everything imported from Postulo comes from ``postulo.plugins.api``. That module is the
promise; every other module in ``postulo`` is this month's internals and may move in a
patch release.

Every string a person reads goes through ``gettext``: the catalogues in ``locale/`` next
to this package translate them, and Postulo picks that directory up when it loads the
plugin. Nothing here is translated by Postulo itself.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from postulo.plugins.api import FieldSpec, TestResult

from . import __version__

#: The environment variable an operator sets to say where this plugin may write.
DIRECTORY_VARIABLE = "POSTULO_HELLOWORLD_DIR"
#: Used when they have not: beside Postulo's own ``data/``, which is the volume that
#: survives an upgrade. An operator who moved that volume sets the variable above.
DEFAULT_DIRECTORY = Path("data") / "helloworld"

#: Characters that make a name into a path. Refused rather than stripped out.
SEPARATORS = ("/", "\\", ":", "\0")


class RefusedName(ValueError):
    """The name given is not a file name. The message is for the person who typed it."""


def directory() -> Path:
    """The one directory this plugin writes in.

    Read on each call rather than at import, so an operator changing the variable does not
    have to think about when the module happened to be loaded.
    """
    return Path(os.environ.get(DIRECTORY_VARIABLE) or DEFAULT_DIRECTORY).expanduser()


def file_for(name: str) -> Path:
    """The file called ``name`` inside :func:`directory`, or :class:`RefusedName`.

    **A person names a file; the operator names the directory. Copy this shape.**

    The first version of this plugin asked for a path and appended to whatever was typed.
    It read as harmless -- writing a line to a file is about as small as an action gets --
    and it was not. A connection's settings are ordinary user input that arrives with the
    *server's* privileges attached, so every account on an instance that installed this
    could append lines to any file the Postulo process may write: ``~/.ssh/authorized_keys``,
    ``~/.bashrc``, a unit file, another person's export. Worse, the appended words come
    from a captured page, so the lines were not even the account holder's to choose: they
    were whatever a stranger put in a job title.

    The fix is not to check the path more cleverly. It is to stop taking one:

    - the field is a **name**, and a separator, a drive letter, a NUL or a leading dot is
      refused rather than cleaned up -- cleaning up invites the next reader to find the one
      spelling the cleaning missed, and the refusal is something a person can read and act
      on, which a silently rewritten path is not;
    - the resolved file is then checked to be directly inside the directory anyway, because
      whether a name escapes is a question for the filesystem (symlinks, names a platform
      shortens) rather than for the string;
    - the directory itself comes from the environment, so widening what this plugin can
      reach is a deployment decision, made by whoever owns the machine.

    It is the rule Postulo already applies to the ``logo=`` a plugin declares. A plugin that
    truly must write outside a directory the operator chose is asking the operator for that,
    not the person filling in a form.
    """
    cleaned = name.strip()
    if not cleaned or cleaned.startswith(".") or any(bad in cleaned for bad in SEPARATORS):
        raise RefusedName(
            str(_("Give the name of a file on its own, not a path: %(name)s is not one."))
            % {"name": cleaned or name}
        )
    root = directory()
    target = root / cleaned
    if target.resolve().parent != root.resolve():
        raise RefusedName(
            str(_("Give the name of a file on its own, not a path: %(name)s is not one."))
            % {"name": cleaned}
        )
    return target


class HelloWorldNotifier:
    # Not `helloworld`, which the source holds: a plugin's name is unique across every
    # kind on an instance -- its switch, its form and its logo are keyed by it -- and
    # Postulo leaves out a second plugin of the same name (postulo/postulo#593).
    name = "helloworld-notifier"
    version = __version__
    #: One of the connected kinds Postulo knows: ``notifier``, ``store`` or ``sync``.
    kind = "notifier"
    #: Shown in the list of plugins a person can connect. Lazy, so it is translated when
    #: displayed, in the reader's language.
    label = gettext_lazy("Hello world")

    def config_fields(self) -> list[FieldSpec]:
        """What the connection form asks for. Postulo builds the form from this."""
        return [
            FieldSpec(
                "file",
                str(_("File name")),
                type="text",
                help=str(
                    _(
                        "A name, not a path: the file is created in the directory this "
                        "instance gives the plugin. Each notification is appended as one line."
                    )
                ),
            ),
            FieldSpec(
                "greeting",
                str(_("Greeting")),
                type="text",
                required=False,
                default="Hello",
                help=str(_("Starts every line, so you can tell this plugin's lines apart.")),
            ),
        ]

    def validate(self, config: dict) -> dict[str, list[str]]:
        """Say no at the form, rather than at three in the morning when a reminder falls due."""
        try:
            file_for(config.get("file", ""))
        except RefusedName as refusal:
            return {"file": [str(refusal)]}
        return {}

    def test(self, config: dict) -> TestResult:
        """Behind the *Test* button: prove the configuration works, in one sentence."""
        try:
            self._append(config, _("This is a test from Postulo."))
        except RefusedName as refusal:
            return TestResult(False, str(refusal))
        except OSError as error:
            # Say what failed, not where: ``str(error)`` carries the file's full path, which
            # is the operator's and which :func:`file_for` keeps out of a person's hands.
            # ``strerror`` is the reason alone ("Permission denied"); an error without one is
            # named by its type. Copy this shape, not ``% {"error": error}``.
            reason = error.strerror or type(error).__name__
            return TestResult(
                False, str(_("Could not write to the file: %(error)s")) % {"error": reason}
            )
        return TestResult(True, str(_("A line was written. Hello, world!")))

    def send(self, notification, config: dict, user) -> None:
        """Carry one notification. Raise on failure: Postulo logs it on the connection."""
        parts = [notification.title]
        if notification.body:
            parts.append(notification.body)
        if notification.url:
            parts.append(notification.url)
        self._append(config, " | ".join(parts))

    @staticmethod
    def _append(config: dict, text: str) -> None:
        target = file_for(config.get("file", ""))
        greeting = config.get("greeting") or "Hello"
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        # One notification, one line. The words can come from a stranger's page, and a
        # newline in a job title would otherwise write a second line that reads like a
        # notification of its own.
        line = " ".join(f"{stamp} {greeting}: {text}".split())
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
