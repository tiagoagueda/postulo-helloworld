"""A notifier: a connected plugin that carries a message somewhere.

A connected plugin describes what it needs from a person as a list of fields, and Postulo
draws the connection form, stores secrets encrypted, offers a *Test* button, and adds a
switch per event. The plugin never renders HTML and never asks which events to deliver: if
``send()`` is called, the person wanted it.

This one appends each notification to a file, which is the simplest thing that can be seen
to work. A real notifier would call a service through ``postulo.plugins.http.client()``,
which carries Postulo's timeouts, user agent and destination policy.

Every string a person reads goes through ``gettext``: the catalogues in ``locale/`` next
to this package translate them, and Postulo picks that directory up when it loads the
plugin. Nothing here is translated by Postulo itself.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from postulo.plugins.base import FieldSpec, TestResult

from . import __version__


class HelloWorldNotifier:
    name = "helloworld"
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
                "path",
                str(_("File to write to")),
                type="text",
                help=str(_("Each notification is appended as one line. The file is created.")),
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

    def test(self, config: dict) -> TestResult:
        """Behind the *Test* button: prove the configuration works, in one sentence."""
        try:
            self._append(config, _("This is a test from Postulo."))
        except OSError as error:
            return TestResult(
                False, str(_("Could not write to the file: %(error)s")) % {"error": error}
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
        path = Path(config["path"]).expanduser()
        greeting = config.get("greeting") or "Hello"
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {greeting}: {text}\n")
