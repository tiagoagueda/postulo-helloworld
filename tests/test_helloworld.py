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


MESSY_PAGE = """<!doctype html>
<html><body>
<header><h1>Hello Jobs</h1></header>
<article data-posting>
  <h1>Research<br>Engineer</h1>
  <p data-company><img src="logo.png">Black<br>Mesa</p>
  <p data-location>Lyon<br>
  <div data-description>We need someone.<br>Apply now.
    <p>Bring a crowbar.
    <p>And a lunch.<hr><img src="x.png">Soon.</div>
  <h1>Not the title</h1>
</article>
<footer><h1>Footer</h1><p data-company>Elsewhere</p></footer>
</body></html>"""


def test_elements_without_an_end_tag_do_not_hold_a_field_open():
    """A `<br>`, an `<img>` or an unclosed `<p>` inside a field leaves the others intact (#9)."""
    posting = HelloWorldSource().parse("https://hello.example/jobs/42", MESSY_PAGE)
    assert posting is not None
    assert posting.title == "Research Engineer", "the site's <h1> is not the posting's"
    assert posting.company_name == "Black Mesa"
    assert posting.location == "Lyon"
    assert posting.description == "We need someone. Apply now. Bring a crowbar. And a lunch.Soon."


def test_a_field_outside_the_posting_is_not_read():
    page = "<h1>Site</h1><p data-company>Elsewhere</p><article data-posting><h1>Job</h1></article>"
    posting = HelloWorldSource().parse("https://hello.example/jobs/1", page)
    assert posting is not None
    assert (posting.title, posting.company_name) == ("Job", "")


def test_a_page_whose_title_is_too_long_is_declined_not_an_error():
    page = f"<article data-posting><h1>{'Engineer ' * 100}</h1></article>"
    assert HelloWorldSource().parse("https://hello.example/jobs/1", page) is None


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
        # What the operating system raises: the reason and the server-side path.
        raise PermissionError(13, "Permission denied", str(directory / "hello.log"))

    monkeypatch.setattr("pathlib.Path.open", refuse)
    result = HelloWorldNotifier().test({"file": "hello.log"})
    assert not result.ok and "Could not write" in result.message
    assert "Permission denied" in result.message, "the reason is said"
    assert str(directory) not in result.message, "the operator's path is not (#13)"
    assert "hello.log" not in result.message


def test_an_error_without_a_reason_is_named_by_its_type_not_by_its_text(directory, monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError(str(directory / "hello.log"))

    monkeypatch.setattr("pathlib.Path.open", refuse)
    result = HelloWorldNotifier().test({"file": "hello.log"})
    assert not result.ok and "OSError" in result.message
    assert str(directory) not in result.message


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
    notifier = registry.find_plugin("notifier", "helloworld-notifier")
    assert notifier is not None and notifier.kind == "notifier"


@pytest.mark.django_db
def test_the_plugin_speaks_french_and_portuguese_by_itself():
    """Postulo's catalogues know nothing of this plugin; its own locale/ is what translates.

    The words are read from the plugin's catalogue rather than written here: translations are
    made in Weblate (postulo/postulo#706), and a speaker improving one must not fail this.
    """
    from pathlib import Path

    from postulo.core import messages_tool

    registry.plugins("notifier", refresh=True)
    notifier = registry.find_plugin("notifier", "helloworld-notifier")
    package = Path(__file__).resolve().parents[1] / "src" / "postulo_helloworld" / "locale"
    for code, directory in (("fr-FR", "fr_FR"), ("pt-PT", "pt_PT")):
        catalogue = messages_tool.parse(
            (package / directory / "LC_MESSAGES" / "django.po").read_text(encoding="utf-8")
        )
        hello = catalogue.messages[(None, "Hello world")].msgstr[0]
        assert hello and hello != "Hello world", f"{code} has no word for the label"
        with translation.override(code):
            assert str(notifier.label) == hello
            field = catalogue.messages[(None, "File name")].msgstr[0]
            assert notifier.config_fields()[0].label == (field or "File name")
    with translation.override("en-GB"):
        assert str(notifier.label) == "Hello world"


def test_the_version_is_read_under_the_name_pyproject_gives_the_distribution():
    """#10: a copy renamed in ``pyproject.toml`` and not in ``__init__.py`` fails on import,
    and one renamed the other way reports whichever plugin of the old name is installed."""
    import ast
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    init = root / "src" / "postulo_helloworld" / "__init__.py"
    names = [
        node.args[0].value
        for node in ast.walk(ast.parse(init.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "version"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert names == [project["name"]]
