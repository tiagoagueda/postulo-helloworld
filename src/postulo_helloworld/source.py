"""A capture source: the four names Postulo looks for, and nothing else.

A source gets a URL and the HTML fetched from it and returns a posting, or ``None``. It
never touches the database and never decides whether its result is good enough: the
person capturing does that on the review screen. So a parser that guesses wrong costs a
few seconds of attention rather than a fabricated job title in somebody's records.

This one reads the tiny page format below, which a real board would never use; the point
is the shape, not the parsing. Replace ``can_handle`` and ``parse`` with your board's.

.. code-block:: html

    <article data-posting>
      <h1>Research Engineer</h1>
      <p data-company>Black Mesa</p>
      <p data-location>Lyon</p>
      <div data-description>We need someone who ...</div>
    </article>
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlsplit

from postulo.plugins.api import JobPostingData

from . import __version__

#: Where this source's pages live. A real source checks its board's hostname.
HOSTS = ("hello.example", "helloworld.example")


def _host_of(url: str) -> str | None:
    """The host of ``url`` when this source's board serves it, otherwise ``None``.

    Exactly one of :data:`HOSTS`, or a subdomain of one on a dot boundary -- so
    ``jobs.hello.example`` is ours and ``nothello.example`` is not.
    """
    host = (urlsplit(url).hostname or "").lower()
    for known in HOSTS:
        if host == known or host.endswith(f".{known}"):
            return host
    return None


class _PostingReader(HTMLParser):
    """Collect the text of the marked elements. Stdlib only, as a plugin may prefer."""

    FIELDS = {"h1": "title", "data-company": "company_name", "data-location": "location"}

    def __init__(self) -> None:
        super().__init__()
        self.found: dict[str, str] = {}
        self._inside: str | None = None
        self._depth = 0
        self.has_marker = False

    def handle_starttag(self, tag: str, attrs) -> None:
        names = {name for name, _value in attrs}
        if "data-posting" in names:
            self.has_marker = True
        if self._inside:
            self._depth += 1
            return
        if tag == "h1":
            self._inside, self._depth = "title", 0
        elif "data-company" in names:
            self._inside, self._depth = "company_name", 0
        elif "data-location" in names:
            self._inside, self._depth = "location", 0
        elif "data-description" in names:
            self._inside, self._depth = "description", 0

    def handle_endtag(self, tag: str) -> None:
        if self._inside is None:
            return
        if self._depth:
            self._depth -= 1
        else:
            self._inside = None

    def handle_data(self, data: str) -> None:
        if self._inside:
            # Raw, so text either side of an inline tag keeps its space; stripped once later.
            self.found[self._inside] = self.found.get(self._inside, "") + data


class HelloWorldSource:
    #: Recorded against every capture this source produced, so a posting can be traced
    #: back to the code that read it.
    name = "helloworld"
    version = __version__

    def can_handle(self, url: str) -> bool:
        """Whether this source wants the page. Cheap, and never fetches anything.

        Compare the **hostname**, never the whole address. ``"hello.example" in url`` also
        answers yes to ``https://evil.test/?hello.example``, and a source that says yes
        gets first refusal on parsing a page it knows nothing about: third-party sources
        are tried before Postulo's own.
        """
        return _host_of(url) is not None

    def parse(self, url: str, html: str) -> JobPostingData | None:
        """The posting on the page, or ``None`` when the page holds none.

        Return ``None`` rather than a half-empty guess: Postulo then tries the next
        source, and the built-in ones are good at pages this one does not understand.
        """
        reader = _PostingReader()
        reader.feed(html)
        found = {key: " ".join(value.split()) for key, value in reader.found.items()}
        if not reader.has_marker or not found.get("title"):
            return None
        return JobPostingData(
            title=found.get("title", ""),
            company_name=found.get("company_name", ""),
            location=found.get("location", ""),
            description=found.get("description", ""),
            url=url,
            # Where it came from, recorded on the capture: the host that served the page,
            # not a constant, so a posting can be told from one read elsewhere.
            source=_host_of(url) or HOSTS[0],
        )
