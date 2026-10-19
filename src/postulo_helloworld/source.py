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


#: HTML elements that never have an end tag. A nesting count that adds one for ``<br>`` and
#: never takes it away again holds a field open until some unrelated end tag, and everything
#: in between is swallowed into it (#9).
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())


#: Start tags that end an open ``<p>`` without its end tag being written (the HTML rule).
CLOSES_A_PARAGRAPH = frozenset(
    "address article aside blockquote div dl fieldset footer form h1 h2 h3 h4 h5 h6 header hr "
    "main nav ol p pre section table ul".split()
)


class _PostingReader(HTMLParser):
    """Collect the text of the marked elements. Stdlib only, as a plugin may prefer.

    Three rules, each of which a hand-rolled parser tends to get wrong:

    - fields are read **only inside** the ``data-posting`` element, so the site's own
      ``<h1>`` in the page header is not the posting's title;
    - a field ends on the end tag of **the element that opened it**, found by counting only
      that tag name, so a stray ``<br>`` or an unclosed ``<p>`` in between cannot keep it
      open (a block-level start tag also ends an open ``<p>`` field, as HTML says it does);
    - each field is read once, from the first element that carries it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.found: dict[str, str] = {}
        self.has_marker = False
        self._posting: str | None = None  # the tag of the data-posting element, while inside
        self._posting_depth = 0
        self._field: str | None = None  # the field being read
        self._field_tag = ""  # ... and the tag that opened it
        self._field_depth = 0
        self._done: set[str] = set()

    def _opens(self, tag: str, names: set[str]) -> str | None:
        """Which field the element starts, if any."""
        if tag == "h1":
            return "title"
        for attribute, field in (
            ("data-company", "company_name"),
            ("data-location", "location"),
            ("data-description", "description"),
        ):
            if attribute in names:
                return field
        return None

    def handle_starttag(self, tag: str, attrs) -> None:
        names = {name for name, _value in attrs}
        if self._posting is None:
            if "data-posting" in names and tag not in VOID:
                self.has_marker = True
                self._posting, self._posting_depth = tag, 0
            return
        if tag == self._posting:
            self._posting_depth += 1
        if self._field is not None:
            if tag == "br":
                self.handle_data(" ")  # a line break separates words, it does not join them
            elif self._field_tag == "p" and tag in CLOSES_A_PARAGRAPH:
                self._field = None  # a block closes an open <p>, written or not
            elif tag == self._field_tag:
                self._field_depth += 1
            if self._field is not None:
                return
        field = self._opens(tag, names)
        if field and field not in self._done and tag not in VOID:
            self._field, self._field_tag, self._field_depth = field, tag, 0
            self._done.add(field)

    def handle_endtag(self, tag: str) -> None:
        if self._posting is None:
            return
        if self._field is not None and tag == self._field_tag:
            if self._field_depth:
                self._field_depth -= 1
            else:
                self._field = None
        if tag == self._posting:
            if self._posting_depth:
                self._posting_depth -= 1
            else:
                self._posting = self._field = None

    def handle_data(self, data: str) -> None:
        if self._field:
            # Raw, so text either side of an inline tag keeps its space; stripped once later.
            self.found[self._field] = self.found.get(self._field, "") + data


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
        try:
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
        except ValueError:
            # A stranger's page can hold a title longer than Postulo keeps. That is a page
            # this source does not understand, not an error: the next source gets a turn.
            return None
