# Lapcare Style Guide

Load this alongside any code-writing task. Rules come with right/wrong pairs; the enforcement
tools (`ruff`, `mypy`, `import-linter`) are configured in `pyproject.toml` and run via
`./check`. When a rule here conflicts with tool output, the tool wins; file a bug against
this document.

## Python

**Formatting/lint:** ruff (format + lint), line length 100, zero warnings. Files/modules are
`snake_case`; one page per directory under `ui/pages/`; a provider file is named after the
tool it wraps (`upower.py`), never the feature it serves.

**Every source file starts with:**

```python
# SPDX-License-Identifier: GPL-3.0-or-later
```

**Types:** full annotations everywhere. `mypy --strict` for `core/` and `providers/`; lenient
for `ui/` (PyGObject stubs are imperfect). No `Any` in a signature without a `# why:` comment.

```python
# RIGHT: frozen dataclass model, Optional-by-default fields
@dataclass(frozen=True)
class BatteryReading:
    charge_full: int | None      # µAh; None on models that don't expose it
    cycle_count: int | None      # None: not exposed; -1 quirk handled in provider

# WRONG: mutable dict-shaped data escaping a provider
def read_battery() -> dict[str, Any]: ...
```

**Interfaces:** `typing.Protocol` in `core/ports.py`. Providers/platform implement them;
nothing outside `app.py` references a concrete implementation.

**Async:** provider/platform I/O is `async def`, scheduled only via `platform/scheduler.py`
(ADR-0007). Core is synchronous and pure. Never block the main loop.

```python
# RIGHT
async def list_batteries(self) -> list[BatteryReading]: ...

# WRONG: thread spun up outside platform/scheduler.py
threading.Thread(target=self._poll).start()
```

**Subprocesses:** only through `platform/subprocess.py` (argv list, absolute whitelisted
binary, scrubbed env, mandatory timeout). `shell=True` never appears in this codebase.

**Errors:** raise only the `core` hierarchy (`ProviderUnavailable`, `ProviderTimeout`,
`ProviderParseError`, `PrivilegedActionDenied`). Translate at the provider boundary; never
`except Exception: pass`.

```python
# RIGHT: translate at the boundary, attach raw payload at DEBUG
try:
    data = json.loads(out)
except json.JSONDecodeError as e:
    log.debug("smartctl raw output: %.2000s", out)
    raise ProviderParseError("smartctl", str(e)) from e

# WRONG: CalledProcessError escaping a provider
```

**Absence vs. inability:** no discrete GPU → empty list (data). Can't ask about GPUs →
`ProviderUnavailable` (state). Never conflate them.

**Docstrings:** every public module/class/function — one summary line plus the non-obvious
(units, failure modes, format quirks). A provider's module docstring must list the exact
sysfs paths / D-Bus interfaces / CLI invocations it touches, with a sample of raw data, plus
kernel/interface stability notes and known model quirks.

**Comments** explain *why* and *constraints* ("cycle_count reads -1 on some EC firmware"),
never *what* the next line does.

**No cleverness:** no metaclasses, no monkeypatching outside tests, no dynamic imports, no
decorators beyond stdlib/GObject ones, no plugin frameworks. Providers are registered in a
plain dict in `app.py`.

## Logging

`logging.getLogger(__name__)` per module; key=value style messages; stderr → journal (no
files, no rotation). Levels: DEBUG raw provider summaries · INFO lifecycle + user actions ·
WARNING degraded states · ERROR failures shown to the user. **Serials/UUIDs/MACs never above
DEBUG.**

## UI

- Layouts in **Blueprint** (`.blp`) only; thin `Gtk.Widget` subclasses bind and forward.
- View-models are plain GObject classes: no widget construction, no GTK-window imports,
  testable without a display. Views contain no business logic — if a view has an `if` about
  hardware, it's in the wrong layer.
- Every page implements the four-state pattern (`loading / ready / unavailable / error`) via
  `Gtk.Stack`; copy the reference page (`ui/pages/placeholder/`, from M0 Commit 12).
- Stock Adwaita widgets (`Adw.ActionRow`, `Adw.PreferencesGroup`, `Adw.StatusPage`,
  `Adw.Banner`) preferred; custom widgets need justification in the PR. GNOME HIG is the
  tiebreaker.
- Any control that triggers a polkit prompt is visually marked (lock emblem); declining auth
  degrades quietly (toast), never an error page.
- All user-visible strings `_()`-wrapped from day one.
- `unavailable` states name the remedy: "Install smartmontools to enable storage health",
  not "No data".

## Tests

Right layer for the behavior: pure logic → `tests/unit/` (no mocks); provider parsing →
fixture-driven `tests/providers/`; D-Bus → python-dbusmock; view-model state transitions →
fake ports, no display; app launch → the one xvfb smoke test. Don't test the kernel, GTK, or
the wrapped tools. Details: `docs/testing.md`.

## Git

Conventional commits, DCO sign-off, small commits, one concern each — see `CONTRIBUTING.md`.
