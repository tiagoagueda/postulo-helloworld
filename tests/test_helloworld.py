"""The plugin, exercised inside a real Postulo: through its registry, as an instance would."""

import pytest
from django.utils import translation
from postulo.notifications.base import Notification
from postulo.plugins import registry
from postulo.plugins.api import JobPostingData, SourcePlugin

from postulo_helloworld import notifier as notifier_module
from postulo_helloworld.notifier import DIRECTORY_VARIABLE, HelloWorldNotifier, RefusedName
from postulo_helloworld.source import HelloWorldSource

# The tests import Postulo freely; the package itself may not, and tests/test_surface.py is
# what holds it to that.


@pytest.fixture
def directory(tmp_path, monkeypatch):
    """The directory the operator gave this plugin, for the length of one test."""
    monkeypatch.setenv(DIRECTORY_VARIABLE, str(tmp_path))
    return tmp_path


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


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/?hello.example",
        "https://evil.test/hello.example/jobs/1",
        "https://hello.example.evil.test/jobs/1",
        "https://nothello.example/jobs/1",
        "https://hello.example@evil.test/jobs/1",
    ],
)
def test_the_source_matches_the_host_and_not_the_address(url):
    """Anything that merely contains the name is somebody else's page."""
    assert not HelloWorldSource().can_handle(url)


@pytest.mark.parametrize(
    "url",
    ["https://hello.example/jobs/1", "http://HELLO.example:8000/x", "https://jobs.hello.example/1"],
)
def test_the_source_takes_its_own_host_and_its_subdomains(url):
    assert HelloWorldSource().can_handle(url)


def test_the_capture_records_the_host_it_came_from():
    posting = HelloWorldSource().parse("https://helloworld.example/jobs/42", PAGE)
    assert posting.source == "helloworld.example"


# ----------------------------------------------------------------- the notifier


def test_the_notifier_writes_one_line_per_message(directory):
    notifier = HelloWorldNotifier()
    config = {"file": "hello.log", "greeting": "Hi"}

    result = notifier.test(config)
    assert result.ok and "Hello, world" in result.message

    notifier.send(
        Notification(
            event="reminder_due", title="Chase Black Mesa", url="https://postulo.example/a/1"
        ),
        config,
        user=None,
    )
    lines = (directory / "hello.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[1].endswith("Hi: Chase Black Mesa | https://postulo.example/a/1")


def test_the_directory_is_made_when_it_is_not_there_yet(tmp_path, monkeypatch):
    monkeypatch.setenv(DIRECTORY_VARIABLE, str(tmp_path / "not" / "yet"))
    assert HelloWorldNotifier().test({"file": "hello.log"}).ok


@pytest.mark.parametrize(
    "name",
    [
        "../../../../etc/cron.d/postulo",
        "/etc/cron.d/postulo",
        "~/.ssh/authorized_keys",
        ".bashrc",
        "sub/hello.log",
        "sub\\hello.log",
        "C:/Windows/system32/x",
        "",
        "   ",
    ],
)
def test_a_path_is_refused_wherever_it_would_have_led(directory, name):
    """The point of the whole exercise: nothing this plugin writes leaves the directory."""
    notifier = HelloWorldNotifier()
    with pytest.raises(RefusedName):
        notifier_module.file_for(name)
    assert notifier.validate({"file": name}), "and the form says so before anything is stored"
    result = notifier.test({"file": name})
    assert not result.ok and "not a path" in result.message


def test_a_plain_name_is_accepted_and_lands_in_the_directory(directory):
    assert HelloWorldNotifier().validate({"file": "hello.log"}) == {}
    assert notifier_module.file_for(" hello.log ") == directory / "hello.log"


def test_a_directory_that_cannot_be_written_to_fails_the_test_button_in_words(
    directory, monkeypatch
):
    def refuse(*args, **kwargs):
        raise PermissionError("read-only file system")

    monkeypatch.setattr("pathlib.Path.open", refuse)
    result = HelloWorldNotifier().test({"file": "hello.log"})
    assert not result.ok and "Could not write" in result.message


def test_one_notification_is_one_line_whatever_the_page_said(directory):
    """The words come from a stranger's posting; a newline in one must not forge a line."""
    HelloWorldNotifier().send(
        Notification(event="capture_received", title="Engineer\nfake line: nothing happened"),
        {"file": "hello.log"},
        user=None,
    )
    assert len((directory / "hello.log").read_text(encoding="utf-8").splitlines()) == 1


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
        assert notifier.config_fields()[0].label == "Nom du fichier"
    with translation.override("pt-pt"):
        assert str(notifier.label) == "Olá, mundo"
    with translation.override("en-gb"):
        assert str(notifier.label) == "Hello world"
