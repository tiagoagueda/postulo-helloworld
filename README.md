# postulo-helloworld

**The smallest [Postulo](https://source.tiagoagueda.com/postulo/postulo) plugin there
is. Copy it to start your own.**

Postulo puts an interface wherever a choice could reasonably vary — where a posting is
read from, how a person is told about things — and its own implementations are plugins
that happen to ship in the box. A plugin written by somebody else is installed with one
command and no change to Postulo. This repository is one such plugin, deliberately tiny,
with everything a real one needs already in place: two kinds of plugin, translations of
its own, tests that run it inside a real Postulo, and a CI workflow.

## What is in the box

| Path | What it is |
| --- | --- |
| `src/postulo_helloworld/source.py` | A **capture source**: four names (`name`, `version`, `can_handle`, `parse`), no base class. Reads a posting out of a tiny page format and returns `JobPostingData`. |
| `src/postulo_helloworld/notifier.py` | A **notifier**, one of the connected plugins: declares the fields it needs, Postulo draws the form, and `send()` appends each notification to a file. The person names the file; the operator names the directory, and `file_for()` explains at length why it is that way round. |
| `src/postulo_helloworld/locale/` | **This plugin's own translations**, French and Portuguese. Postulo never translates a plugin's strings; every plugin holds its locale. The directories carry gettext's names (`fr_FR`, `pt_PT`), written by a tool; everywhere else a language is `fr-FR`, as *Make it yours* explains. |
| `tests/` | Runs both plugins through Postulo's registry, exactly as an instance would, and checks the French comes from this package. `tests/test_surface.py` fails on an import that reaches past `postulo.plugins.api`, by calling the core's own `postulo.plugins.testing` — do that rather than copying this file. `tests/settings.py` is Postulo's test configuration, borrowed. |
| `pyproject.toml` | The entry points that make the plugins appear, and nothing else: a plugin has no dependencies of its own, it runs inside Postulo's environment. |
| `.forgejo/ISSUE_TEMPLATE/` | **The issue forms**: *Bug report* and *Feature request*, and the links shown above them. Report a problem with this plugin through them. A plugin's own repository wants its own forms: copy these, change the names, the fields and the links, and keep the link to Postulo's `SECURITY.md` and the warning about personal details. |
| `.forgejo/workflows/` | **The CI**: `ci.yml` (lint, catalogues, tests, and the dependency audit as its own job), `weekly.yml` (the audit alone, every Monday) and `release.yml` (the release gate, on a tag). Each step is a call to the shared plugin action, [Postulo/plugin-ci](https://source.tiagoagueda.com/Postulo/plugin-ci), by its full address, so a new plugin copies these three files as they are and a change to the plugin CI (a uv bump) is made there once. Its README lists the inputs, such as extra Debian packages. |

## Try it

Into the environment of a running Postulo:

```sh
uv pip install git+https://source.tiagoagueda.com/postulo/postulo-helloworld.git
```

Restart Postulo. **Capture a posting** from any address on `hello.example` and the source
answers; under **Settings → Connections → Add**, *Hello world* is offered, asks for a
file name, and its *Test* button writes a line. That is the whole installation;
uninstalling the package removes both.

The lines go to `data/helloworld/` beside Postulo's own data, or wherever
`POSTULO_HELLOWORLD_DIR` points. Nothing a person types moves that: the field is a name,
never a path.

## Make it yours

1. Copy the repository and rename it everywhere the name lives, or the copy will not
   import. The package is `postulo_helloworld`, the distribution `postulo-helloworld`
   (`postulo-messages` finds the package from the distribution's name, hyphens read as
   underscores), and between them they are written in:
   - the directory `src/postulo_helloworld/`;
   - `pyproject.toml`: `[project] name`, `[tool.hatch.build.targets.wheel] packages` and
     `artifacts`, and the entry points (step 3);
   - `src/postulo_helloworld/__init__.py`: the distribution's name in `version(...)`, which
     raises `PackageNotFoundError` on import once nothing of that name is installed;
   - `tests/test_surface.py`: `PACKAGE`.

   `tests/test_helloworld.py` fails while `__init__.py` and `[project] name` disagree.
2. Keep or delete either plugin; a package may hold one kind or several.
3. Change the entry points in `pyproject.toml` to point at your classes. The groups are
   `postulo.sources`, `postulo.importers`, `postulo.notifiers`, `postulo.outboxes`,
   `postulo.stores`, `postulo.syncs`, `postulo.transports`, `postulo.features`,
   `postulo.link_services`, `postulo.messaging_services`, `postulo.register_adapters` and
   `postulo.backups`, and the class each expects is on `postulo.plugins.api`. A plugin's
   `name` is unique across every kind on an instance -- its switch, its form and its logo are
   keyed by it, and Postulo leaves out a second plugin of the same name -- which is why the
   source here is `helloworld` and the notifier `helloworld-notifier`.
4. Wrap every string a person reads in `gettext` / `gettext_lazy`, then:

   ```sh
   uv run postulo-messages extract   # a catalogue for every language Postulo offers
   uv run postulo-messages compile   # writes the .mo files, no gettext needed
   ```

   Postulo's own catalogue tool, installed with Postulo as a dev dependency. Do not
   commit the `.mo` files: `compile` writes them before the tests and before `uv build`,
   and `pyproject.toml` puts them in the wheel. English is the source. **Translate your
   plugin wherever you like**; the official plugins, this one included, are translated in
   Weblate at translate.tiagoagueda.com and never in a commit (`uv run postulo-messages
   guard` refuses one, postulo/postulo#706), and `uv run pytest -m release` holds the
   languages the paired core release selects complete before a release.

   **A language code is a BCP 47 tag in its canonical form**: the language in lower
   case, a script with a capital, a region in capitals — `fr-FR`, `pt-BR`, `sr-Cyrl`.
   That is how Postulo writes every code it hands you (`Notification.language`,
   `DocumentMetadata.language`) and how you write one in code, in tests and in what you
   store or send. The directories under `locale/` are the one exception, and not yours to
   spell: `pt_BR` and `sr_Cyrl` are gettext's names for a catalogue, which
   `postulo-messages` derives from the tags, so nobody types one. A code that comes from
   outside — a form, a file, another service — may be spelt any way: put it in the
   canonical form with `language_tag`, check that it is one with `is_language_tag`, and
   find the nearest of the languages you have with `language_match`, all from
   `postulo.plugins.api`. `tests/test_catalogues.py` fails on a code written in lower
   case anywhere in the repository.
5. Run the tests:

   ```sh
   uv sync        # brings in Postulo itself from its repository, for the tests
   uv run pytest
   ```

The contract in full — every field of `JobPostingData`, how sources are chosen, what a
connected plugin's `config_fields()` and `test()` must do, how to add a settings section —
is in the wiki's
[Writing a plugin](https://source.tiagoagueda.com/postulo/postulo/wiki/Writing-a-plugin);
the names you may use are the ones in `postulo.plugins.api.__all__`.

## Rules worth keeping

- **Leave a field empty rather than guessing.** A blank box on the review screen invites
  typing; a confidently wrong value has to be noticed first.
- **Return `None` when the page is not yours.** Postulo tries the next source.
- **A person names a thing; the operator names the place.** A connection's settings are
  ordinary user input handed to you with the server's privileges attached, so a field that
  takes a path lets any account on the instance reach any file the process may write. Take
  a name, refuse a separator rather than cleaning it out, and put the directory in the
  environment.
- **Match the host, not the address.** `"board.example" in url` also says yes to
  `https://evil.test/?board.example`, and a source that says yes is parsing a stranger's
  page ahead of Postulo's own parsers.
- **Import `postulo.plugins.api` and nothing else from Postulo.** Everything else is
  internals that may be renamed in a patch release; `tests/test_surface.py` holds you to it.
- **Use `postulo.plugins.api.client()` for every request** a connected plugin makes. It
  carries Postulo's timeouts, user agent and destination policy.
- **Raise on failure in `send()`.** Postulo logs it and shows it on the connection; it
  never fails whatever caused the notification.
- **Translate your own strings.** Ship `locale/`; Postulo reads it when it loads you.
- **Write a language code the way Postulo does: `pt-BR`.** A BCP 47 tag in its canonical
  form, everywhere but the names of the `locale/` directories. Compare two with
  `language_match`, never with `==`: tags are the same whatever their case, and `pt-BR`
  asked of a plugin that only has `pt` should find it.

## Licence

MIT, so that copying it into your own plugin is a decision you never have to think about.
Postulo itself is AGPL-3.0-or-later.

The copyright line in `LICENSE` and the `authors` entry in `pyproject.toml` name the Postulo
contributors because this repository is theirs. When you start your own plugin from it,
replace both with your own name (or your organisation's).
