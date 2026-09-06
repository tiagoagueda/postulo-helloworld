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
| `src/postulo_helloworld/notifier.py` | A **notifier**, one of the connected plugins: declares the fields it needs, Postulo draws the form, and `send()` appends each notification to a file. |
| `src/postulo_helloworld/locale/` | **This plugin's own translations**, French and Portuguese. Postulo never translates a plugin's strings; every plugin holds its locale. |
| `scripts/compile_messages.py` | Turns the `.po` catalogues into the `.mo` files Django reads, in pure Python, so no gettext installation is needed. |
| `tests/` | Runs both plugins through Postulo's registry, exactly as an instance would, and checks the French comes from this package. `tests/settings.py` is Postulo's test configuration, borrowed. |
| `pyproject.toml` | The entry points that make the plugins appear, and nothing else: a plugin has no dependencies of its own, it runs inside Postulo's environment. |

## Try it

Into the environment of a running Postulo:

```sh
uv pip install git+https://source.tiagoagueda.com/postulo/postulo-helloworld.git
```

Restart Postulo. **Capture a posting** from any address on `hello.example` and the source
answers; under **Settings → Connections → Add**, *Hello world* is offered, asks for a
file path, and its *Test* button writes a line. That is the whole installation;
uninstalling the package removes both.

## Make it yours

1. Copy the repository and rename `postulo_helloworld` to your package.
2. Keep or delete either plugin; a package may hold one kind or several.
3. Change the entry points in `pyproject.toml` to point at your classes. The groups are
   `postulo.sources`, `postulo.notifiers`, `postulo.stores` and `postulo.syncs`.
4. Wrap every string a person reads in `gettext` / `gettext_lazy`, then:

   ```sh
   django-admin makemessages --locale fr_FR --locale pt_PT   # writes locale/*/django.po
   python scripts/compile_messages.py                         # writes the .mo files
   ```

   Commit the `.mo` files: they ship with the package.
5. Run the tests:

   ```sh
   uv sync        # brings in Postulo itself from its repository, for the tests
   uv run pytest
   ```

The contract in full — every field of `JobPostingData`, how sources are chosen, what a
connected plugin's `config_fields()` and `test()` must do, how to add a settings section —
is in Postulo's
[docs/PLUGINS.md](https://source.tiagoagueda.com/postulo/postulo/src/branch/main/docs/PLUGINS.md).

## Rules worth keeping

- **Leave a field empty rather than guessing.** A blank box on the review screen invites
  typing; a confidently wrong value has to be noticed first.
- **Return `None` when the page is not yours.** Postulo tries the next source.
- **Use `postulo.plugins.http.client()` for every request** a connected plugin makes. It
  carries Postulo's timeouts, user agent and destination policy.
- **Raise on failure in `send()`.** Postulo logs it and shows it on the connection; it
  never fails whatever caused the notification.
- **Translate your own strings.** Ship `locale/`; Postulo reads it when it loads you.

## Licence

MIT, so that copying it into your own plugin is a decision you never have to think about.
Postulo itself is AGPL-3.0-or-later.
