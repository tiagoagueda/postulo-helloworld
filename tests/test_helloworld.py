"""The plugin, exercised inside a real Postulo: through its registry, as an instance would."""

import pytest
from django.utils import translation
from postulo.notifications.base import Notification
from postulo.plugins import registry
from postulo.plugins.base import JobPostingData, SourcePlugin

from postulo_helloworld.notifier import HelloWorldNotifier
from postulo_helloworld.source import HelloWorldSource

PAGE = """<!doctype html>
<html><body>
<article data-posting>
  <h1>Research Engineer</h1>
  <p data-company>Black Mesa</p>
  <p data-location>Lyon</p>
  <div data-description>We need someone who <em>likes</em> physics.</div>
</article>
</body></html>"""


# ------------------------------------------------------------------- the source


def test_the_source_is_a_source():
    assert isinstance(HelloWorldSource(), SourcePlugin), "the four names are all it takes"


def test_the_source_reads_the_page_it_understands():
    source = HelloWorldSource()
    assert source.can_handle("https://hello.example/jobs/42")
    posting = source.parse("https://hello.example/jobs/42", PAGE)
    assert isinstance(posting, JobPostingData)
    assert posting.title == "Research Engineer"
    assert posting.company_name == "Black Mesa"
    assert posting.location == "Lyon"
    assert posting.description == "We need someone who likes physics."
    assert posting.url == "https://hello.example/jobs/42"


def test_the_source_declines_what_it_does_not_understand():
    source = HelloWorldSource()
    assert not source.can_handle("https://example.org/jobs/1")
    assert source.parse("https://hello.example/about", "<h1>About us</h1>") is None, (
        "no marker, so None: Postulo tries the next source"
    )


# ----------------------------------------------------------------- the notifier


def test_the_notifier_writes_one_line_per_message(tmp_path):
    target = tmp_path / "hello.log"
    notifier = HelloWorldNotifier()
    config = {"path": str(target), "greeting": "Hi"}

    result = notifier.test(config)
    assert result.ok and "Hello, world" in result.message

    notifier.send(
        Notification(
            event="reminder_due", title="Chase Black Mesa", url="https://postulo.example/a/1"
        ),
        config,
        user=None,
    )
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[1].endswith("Hi: Chase Black Mesa | https://postulo.example/a/1")


def test_a_bad_path_fails_the_test_button_in_words(tmp_path):
    result = HelloWorldNotifier().test({"path": str(tmp_path / "no" / "such" / "dir" / "x")})
    assert not result.ok and "Could not write" in result.message


# ------------------------------------------------------------------ in Postulo


@pytest.mark.django_db
def test_postulo_finds_both_plugins_through_their_entry_points():
    sources = {plugin.name for plugin in registry.plugins("source", refresh=True)}
    assert "helloworld" in sources
    notifier = registry.find_plugin("notifier", "helloworld")
    assert notifier is not None and notifier.kind == "notifier"


@pytest.mark.django_db
def test_the_plugin_speaks_french_and_portuguese_by_itself():
    """Postulo's catalogues know nothing of this plugin; its own locale/ is what translates."""
    registry.plugins("notifier", refresh=True)
    notifier = registry.find_plugin("notifier", "helloworld")
    with translation.override("fr-fr"):
        assert str(notifier.label) == "Bonjour le monde"
        assert notifier.config_fields()[0].label == "Fichier dans lequel écrire"
    with translation.override("pt-pt"):
        assert str(notifier.label) == "Olá, mundo"
    with translation.override("en-gb"):
        assert str(notifier.label) == "Hello world"
