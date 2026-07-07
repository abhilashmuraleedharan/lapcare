# LapCare — Engineering Plan & Repository Blueprint

> A Linux-native system management application for Lenovo ThinkPads (and, eventually, other laptops).
> Working codename: **LapCare** (`lapcare`). The final name is deliberately deferred — "Vantage",
> "ThinkPad", and "Lenovo" are trademarks and must not appear in the product name. Naming is ADR-0001.

**Status:** Planning. No implementation exists yet.
**Document owner:** Lead Architect.
**Version:** 1.1 — revised after Principal Engineer architecture review; dispositions recorded
in `lapcare-review-reconciliation.md`.
**Last updated:** 2026-07-06.

---

## 1. Product Vision

LapCare is a polished, modern desktop application for Ubuntu (and other Linux distributions)
that gives ThinkPad owners the system insight and hardware management they lost when they left
Windows and Lenovo Vantage behind.

It is explicitly **an integration layer, not a reimplementation layer**. Linux already has
excellent hardware tooling — `fwupd`, `upower`, `smartctl`, `lm-sensors`, `thinkpad_acpi`,
`dmidecode` — but it is scattered across CLIs, D-Bus services, and sysfs files that ordinary
users never discover. LapCare's job is to orchestrate those tools behind one coherent,
native-feeling UI.

**One-sentence pitch:** *"Everything your ThinkPad can tell you, in one window."*

Success looks like:
- A ThinkPad user installs one package and immediately sees hardware info, battery health,
  firmware update status, and a health score — with zero terminal usage.
- A support forum answer changes from "run these 6 commands and paste the output" to
  "export a diagnostic report from LapCare and attach it."
- Contributors and AI agents can add a new hardware provider in an afternoon because the
  module boundaries and documentation make the extension point obvious.

## 2. Guiding Principles

1. **Wrap, don't reimplement.** If a maintained Linux tool or kernel interface exposes the data,
   consume it. We write UI, orchestration, and interpretation — never device drivers or parsers
   for things that have a stable structured interface.
2. **Prefer structured interfaces over scraping.** D-Bus > sysfs > CLI with `--json` > CLI text
   parsing. Text parsing is a last resort and must be isolated behind a provider so it can be
   replaced.
3. **Degrade gracefully.** Every feature must handle "this tool isn't installed", "this isn't a
   ThinkPad", and "permission denied" as first-class states with helpful UI, not crashes.
4. **Least privilege, always.** The app runs as the user. Privileged operations go through
   narrowly-scoped polkit actions. No `sudo`, no setuid, no long-running root daemon in the MVP.
5. **Read-only by default.** The MVP observes; it does not mutate hardware state. Writes
   (charge thresholds, BIOS settings) come later, individually, behind explicit polkit actions.
6. **Boring technology.** Choose tools that will still be maintained in 2036. Minimize
   dependencies; every dependency is a liability we adopt.
7. **Modular, not micro.** Clear module boundaries with plain interfaces — but one process, one
   repo, one language until proven insufficient.
8. **Agent-legible.** The repository is structured so an AI coding agent (or a new human
   contributor) can locate the architecture, conventions, current status, and past decisions in
   under five minutes of reading.
9. **Simplicity beats cleverness.** A 30-line explicit function beats a 5-line metaprogrammed one.

## 3. Architecture Overview

Single desktop process with strictly layered internals, plus an optional short-lived privileged
helper invoked through polkit.

```
┌───────────────────────────────────────────────────────────┐
│  UI Layer (GTK4 + libadwaita)                             │
│  Pages, widgets, view-models. No system access.           │
├───────────────────────────────────────────────────────────┤
│  Core / Domain Layer (pure Python)                        │
│  Models (Battery, Firmware, Device…), health scoring,     │
│  wear analysis, diagnostics engine, report rendering —    │
│  plus core/ports.py: the Protocol interfaces that         │
│  providers and platform implement. No GTK imports. No     │
│  I/O of any kind. Fully unit-testable.                    │
├───────────────────────────────────────────────────────────┤
│  Provider Layer (integration adapters)                    │
│  upower (D-Bus) · fwupd (D-Bus) · sysfs readers ·         │
│  thinkpad_acpi · dmidecode · smartctl/nvme-cli ·          │
│  lm-sensors. One provider per data source, each behind    │
│  a small interface, each individually fakeable in tests.  │
├───────────────────────────────────────────────────────────┤
│  Platform Layer                                           │
│  D-Bus session/system connections, subprocess runner,     │
│  polkit-mediated privileged helper client, logging.       │
└───────────────────────────────────────────────────────────┘
        │ pkexec (polkit)                    │ D-Bus (system bus)
        ▼                                    ▼
┌──────────────────────┐        ┌───────────────────────────┐
│ lapcare-helper       │        │ Existing system services  │
│ short-lived root     │        │ UPower, fwupd, logind …   │
│ helper for the few   │        │ (they do their own polkit │
│ reads that need root │        │  enforcement)             │
└──────────────────────┘        └───────────────────────────┘
```

Data flow rule: **ports-and-adapters around a pure core.** The core defines models and the
`core/ports.py` Protocol interfaces; providers and platform *implement* those ports; the UI
depends on **core only** (plus GTK); the composition root (`app.py`) is the only module that
sees concrete implementations and wires them together. The core never imports GTK, providers,
or platform; nothing performs I/O except providers/platform. This is the single most important
invariant in the codebase and is enforced by an import-linter rule in CI.

A related distinction worth stating: layering controls **blast radius** (a hardware quirk stays
inside one provider) — it does not control hardware *variance*. Variance is controlled by the
fixture corpus, nullable-by-default model fields, and the availability contract (§6, §15).

Concurrency model: GTK main loop on the main thread. All provider I/O (D-Bus calls, subprocess
runs, sysfs reads that might block) runs via `asyncio` integrated with the GLib main loop.
**Compatibility caveat:** PyGObject's native asyncio integration (`gi.events`) landed in
PyGObject 3.50, but Ubuntu 24.04 LTS ships 3.48 — so M0 includes a stack-validation spike on
every supported LTS. The sanctioned fallback where `gi.events` is unavailable: a **single
shared thread-pool executor owned by `platform/`**, marshaling results back via
`GLib.idle_add`. No *ad-hoc* threads anywhere else — the platform executor is the one
exception, behind one interface, chosen per-LTS at startup.

## 4. Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| Language | **Python 3.12+** | Best-in-class for glue/orchestration work (which is 90% of this app), huge contributor pool, excellent AI-agent legibility, first-class GObject bindings. Performance is irrelevant here — the app reads sysfs files and makes D-Bus calls. |
| UI toolkit | **GTK4 + libadwaita** (via PyGObject) | See §5. |
| UI definition | **Blueprint** (`.blp` → compiled to GTK Builder XML) | Declarative, diff-friendly, the modern GNOME convention; far more agent-editable than imperative widget code. |
| D-Bus | **GLib GDBus via PyGObject** | Already in-process with GTK; no extra dependency (`dbus-python` and `pydbus` are avoided). |
| Async | **asyncio + GLib event loop integration** (`gi.events`, PyGObject ≥ 3.50); platform-owned thread-pool executor fallback on older LTS | One concurrency model everywhere; the version constraint is validated in M0 (§3). |
| Settings | **GSettings** (schema in `data/`, thin `platform/settings.py` wrapper) | Native, observable, dconf-backed; covers units, privacy defaults, report options. No custom config files. |
| Build system | **Meson** | The GNOME-ecosystem standard: handles gschemas, desktop file, icons, translations, blueprint compilation, and polkit policy installation in one place. Install paths (libexecdir, polkit policy dir) are Meson options for distro portability. |
| Lint/format | **ruff** (lint + format) | One fast tool instead of flake8+isort+black. |
| Types | **mypy (strict in `core/` and `providers/`)** | Type contracts are documentation agents can rely on. UI layer checked leniently (PyGObject stubs are imperfect). |
| Tests | **pytest**, **python-dbusmock**, fixture corpus of captured real command outputs | See §15. |
| Packaging | **.deb** (primary, via PPA), source tarball; Flatpak deferred | See §17. |
| Versioning | SemVer, `CHANGELOG.md` (Keep a Changelog format) | Boring and standard. |

Runtime dependencies (deliberately short): GTK4, libadwaita ≥ 1.4, PyGObject, and the wrapped
system tools — of which only `upower` and `fwupd` are hard-ish dependencies (both preinstalled
on Ubuntu Desktop). `smartmontools`, `nvme-cli`, `lm-sensors`, `dmidecode` are *optional*:
their absence degrades the relevant panel to an "install X to enable this" state.

**Considered and rejected:** Rust + gtk4-rs (excellent fit technically, but slower iteration
and a smaller contributor/agent success rate for UI-heavy glue code; revisit only if we ever
need a long-running system daemon, which could be a small separate Rust binary). Electron
(footprint and non-native feel are disqualifying for a system utility).

## 5. Desktop Framework Recommendation

**Recommendation: GTK4 + libadwaita, in Python via PyGObject.**

Justification:

1. **Target-platform nativeness.** Ubuntu Desktop is GNOME. A libadwaita app inherits the
   platform's look, dark-mode handling, HIG-compliant adaptive layouts, and accessibility stack
   for free. A "Lenovo Vantage for Linux" that looks like a foreign transplant defeats its own
   purpose. Lenovo Vantage's own information-dense-but-clean layout maps naturally onto
   libadwaita's `NavigationSplitView` + preference-group idiom.
2. **The integration surface is GLib-shaped.** UPower, fwupd, logind, and NetworkManager are all
   D-Bus services; GDBus is part of GLib, which we get for free with GTK. Qt would add its own
   D-Bus layer; Tauri would need a Rust backend speaking zbus plus a JS frontend — two languages
   and an IPC boundary for no benefit.
3. **Against Qt6:** technically excellent, but Qt apps look and feel non-native on GNOME,
   PyQt/PySide licensing and packaging are heavier, and KDE users are better served later by
   good theming than by choosing Qt now.
4. **Against Tauri/Electron:** a webview UI for a hardware utility inverts the effort profile —
   we'd spend our complexity budget on an IPC bridge and web build tooling instead of features.
   Bundle size, memory, and sandbox friction (webview + system access) all point the wrong way.
5. **Longevity:** GTK4/libadwaita is the actively developed toolkit of the platform we target,
   with a 10+ year support horizon and a thriving ecosystem of similar apps to imitate
   (GNOME Firmware, Mission Center, Usage) — real reference implementations agents can learn from.

Trade-off accepted: GTK4 is GNOME-centric; KDE/other-DE users get a functional but
GNOME-flavored app. Acceptable for an Ubuntu-first product. Stated positioning: **GNOME-first,
distro-portable where practical** — and we will *not* abstract the UI toolkit to hedge this;
a toolkit-abstraction layer would cost more than it could ever save here.

## 6. Backend Architecture

The "backend" is the in-process **provider layer** plus the out-of-process **privileged helper**.

### Providers

Each external data source gets exactly one provider module implementing a small typed interface.
**The interfaces (ports) live in `core/ports.py`** — `Protocol` definitions are typing-only, so
the core stays pure while owning the contracts; providers are the adapters that implement them:

```python
# core/ports.py
class BatteryProvider(Protocol):
    async def list_batteries(self) -> list[BatteryReading]: ...
    def subscribe(self, callback: Callable[[BatteryReading], None]) -> Subscription: ...
```

Planned providers and their transport (in preference order per §2.2):

| Provider | Source | Transport | Privilege |
|---|---|---|---|
| `upower` | Battery/AC state, history | D-Bus `org.freedesktop.UPower` | none |
| `battery_sysfs` | Wear data: `charge_full`, `charge_full_design`, `cycle_count` | `/sys/class/power_supply/BAT*/` | none |
| `fwupd` | Firmware devices, releases, updates | D-Bus `org.freedesktop.fwupd` | fwupd's own polkit |
| `dmi` | Model, serial, BIOS version | `/sys/class/dmi/id/` (unprivileged fields); `dmidecode` via helper only for the few root-only fields | mostly none |
| `thinkpad_acpi` | ThinkPad detection, fan speed, thermal, LEDs | `/sys/devices/platform/thinkpad_acpi/`, `/proc/acpi/ibm/` | none (read) |
| `hwmon` | Temperatures, fan RPM | `/sys/class/hwmon/` (read directly; no `sensors` CLI dependency) | none |
| `storage_smart` | SMART/NVMe health | `smartctl --json`, `nvme --output-format=json` via helper | root (via polkit) |
| `pci_usb` | Device inventory | `lspci -mm`, `lsusb` (or direct sysfs walk) | none |
| `os_info` | Kernel, distro, uptime | `/etc/os-release`, `/proc` | none |

Provider rules:
- A provider owns **all** knowledge of its source's quirks (paths, JSON schemas, text formats).
  Nothing outside the provider may parse that source's output.
- Every provider returns **core-layer dataclasses**, never raw dicts/strings.
- Every provider implements `availability() -> Availability` reporting `OK / TOOL_MISSING /
  UNSUPPORTED_HARDWARE / PERMISSION_DENIED`, which the UI renders as guided empty-states.
  This contract is deliberately the **seed of a future capability model**: a fuller
  per-capability scheme (`supports_battery_thresholds`, …) is *not* built now — it becomes an
  ADR when the first write feature (M6) or second hardware vendor (M10) arrives, whichever is
  first. Building it with one vendor and zero write features would be speculative structure.
- Every model field is **`Optional` unless the fixture corpus proves it universal**; provider
  docs must include kernel/interface stability notes and known per-model quirks.
- Providers are registered in a plain dict at startup — no plugin framework, no entry points,
  no dynamic discovery. Adding a provider = add a module + one registry line.

### Core layer

Pure, synchronous, dependency-free Python — **no I/O of any kind**. Persistence and file
output are explicitly *not* core: core defines `HistoryStore` and `ReportWriter` ports in
`core/ports.py`; the SQLite implementation (daily snapshots in `~/.local/share/lapcare/`) and
filesystem writer live in `platform/`. Core computes; platform stores. Contains:
- **Models:** `Battery`, `FirmwareDevice`, `StorageDevice`, `ThermalZone`, `SystemInfo`,
  `HealthReport` — frozen dataclasses, fields `Optional` by default (§6 provider rules).
- **Ports (`core/ports.py`):** the Protocol interfaces implemented by providers
  (BatteryProvider, FirmwareProvider, …) and platform (HistoryStore, ReportWriter).
- **Battery wear analysis:** wear % = `1 − charge_full/charge_full_design`, cycle-count
  interpretation, thresholds for good/fair/poor, trend computation over history handed to it
  by the app layer.
- **Health scoring:** a transparent, documented rubric combining battery wear, SMART status,
  firmware currency, and thermal headroom. No ML, no magic — every score must be explainable
  in the UI ("−15: battery wear above 20%"). Each signal carries a **confidence/coverage
  marker** ("cycle count unavailable on this model — excluded from score"), and the aggregate
  number ships **labeled experimental** and visually de-emphasized until the fixture corpus
  demonstrates calibration across enough models (revisit at M5).
- **Diagnostics engine:** an ordered list of `Check` objects (`id`, `title`, `run(snapshot) →
  Pass/Warn/Fail + explanation + remediation hint`). Checks are pure functions over a
  `SystemSnapshot`, so they're trivially unit-testable.
- **Report exporter:** renders a `SystemSnapshot` + diagnostics to Markdown/HTML/JSON strings
  (pure), with a privacy toggle that redacts serial numbers and UUIDs. Writing the file is the
  app layer's job via the `ReportWriter` port.

### Privileged helper (`lapcare-helper`)

A single small Python script installed to `/usr/libexec/lapcare/`, invoked via
`pkexec /usr/libexec/lapcare/lapcare-helper <verb>` with a **fixed verb whitelist**
(`smart-report <device-name>`, `nvme-report <device-name>`, `dmi-full`). It runs the
corresponding tool with hardcoded, safe argument construction, prints JSON to stdout, and
exits. It accepts no free-form arguments, sources no user-controlled config, and each verb maps
to one polkit action (§14). It is short-lived — no daemon, no socket, no state.

Device targeting is **enumerate-and-match, not input validation**: the helper never accepts a
device *path*. It takes a bare device *name* (e.g. `nvme0n1`), enumerates `/sys/block` itself,
and refuses anything not in that enumeration — so there is no path/symlink/regex surface to get
wrong. The full threat model and validation spec is **ADR-0006, a blocking entry gate for M4**
(§14, §19).

## 7. UI Architecture

- **Shell:** `Adw.ApplicationWindow` with `Adw.NavigationSplitView` — sidebar of pages
  (Dashboard, Hardware, Battery, Firmware, Storage, Diagnostics), content pane per page.
  Adaptive down to narrow widths for free.
- **Pattern: lightweight MVVM.**
  - *Views* are Blueprint files plus thin `Gtk.Widget` subclasses that only bind and forward.
  - *View-models* are plain `GObject` classes exposing properties/signals; they call core/provider
    APIs asynchronously and translate results into displayable state. They contain no widget
    construction and are testable without a display.
  - *No business logic in views.* If a view has an `if` about hardware, it's in the wrong layer.
- **State pattern per page:** every page renders one of four states — `loading`, `ready`,
  `unavailable(reason, remedy)`, `error(detail)` — via `Gtk.Stack`. This is a hard convention;
  it's what makes graceful degradation systematic instead of ad hoc.
- **Live updates:** view-models subscribe to provider signals (UPower/fwupd D-Bus signals);
  polling only where no signal exists (hwmon: 2s while the page is visible, paused when not).
- **Progressive startup:** providers are lazily initialized per page; the Dashboard renders
  cheap/cached signals first (DMI identity, last-known battery snapshot) and enriches
  asynchronously. The cold-start target (§19 M5) is defined as *window + first meaningful
  dashboard content*, not all-providers-probed.
- **Widgets:** prefer stock libadwaita (`Adw.ActionRow`, `Adw.PreferencesGroup`,
  `Adw.StatusPage`, `Adw.Banner`). Custom widgets require justification in the PR.
- **HIG compliance:** GNOME Human Interface Guidelines are the tiebreaker for all UI arguments.

## 8. Module Boundaries

Python package `lapcare` with enforced import rules (checked in CI via `import-linter`):

| Module | May import | Must not import |
|---|---|---|
| `lapcare/core/` (incl. `ports.py`) | stdlib only | GTK/GLib, providers, platform, ui |
| `lapcare/providers/` | core (models + ports), platform | ui |
| `lapcare/platform/` | stdlib, GLib, core ports (to implement them) | providers, ui |
| `lapcare/ui/` | **core only** (models + ports), GTK/Adw | providers, platform |
| `lapcare/app.py` | everything (composition root) | — |
| `helper/` (separate top-level) | stdlib only | anything in `lapcare` |

The UI never names a concrete provider: it receives port implementations from the composition
root. This closes the v1.0 inconsistency where the UI imported `providers/base.py` — provider
protocols now live in `core/ports.py`, so the dependency arrows all point inward to core.

The composition root (`app.py`) is the only place where concrete providers are constructed and
wired to view-models. Everything else depends on interfaces. This is dependency injection by
hand — no DI framework.

## 9. Project Directory Layout

```
lapcare/
├── AGENTS.md                  # Entry point for AI agents (see §"Agent-first")
├── ARCHITECTURE.md            # One-page architecture summary → links into docs/
├── CONTRIBUTING.md            # Human + agent contribution workflow
├── ROADMAP.md                 # Milestones and current status
├── DECISIONS.md               # ADR index (decisions live in docs/adr/)
├── STYLEGUIDE.md              # Coding & UI conventions
├── SECURITY.md                # Vulnerability reporting (required before M4 ships the helper)
├── README.md                  # User-facing: what, screenshots, install
├── CHANGELOG.md
├── LICENSE                    # GPL-3.0-or-later (ADR-0002)
├── run                        # dev wrapper: build + launch
├── check                      # dev wrapper: lint + types + import rules + tests (mirrors CI fast lane)
├── meson.build
├── pyproject.toml             # ruff, mypy, pytest config
├── src/
│   └── lapcare/
│       ├── app.py             # Adw.Application, composition root
│       ├── core/
│       │   ├── models.py
│       │   ├── ports.py       # ALL Protocol interfaces: providers + HistoryStore/ReportWriter
│       │   ├── battery_analysis.py
│       │   ├── health_score.py
│       │   ├── diagnostics/   # one file per check group
│       │   └── report.py      # renders to strings; never touches the filesystem
│       ├── providers/
│       │   ├── availability.py  # Availability enum/helpers shared by adapters
│       │   ├── upower.py
│       │   ├── fwupd.py
│       │   ├── battery_sysfs.py
│       │   ├── thinkpad_acpi.py
│       │   ├── hwmon.py
│       │   ├── dmi.py
│       │   ├── storage_smart.py
│       │   └── ...
│       ├── platform/
│       │   ├── dbus.py        # bus connections, proxy helpers
│       │   ├── subprocess.py  # single audited runner (timeouts, no shell=True)
│       │   ├── privileged.py  # pkexec helper client
│       │   ├── history.py     # SQLite HistoryStore (implements core port)
│       │   ├── report_writer.py # filesystem ReportWriter (implements core port)
│       │   ├── settings.py    # thin GSettings wrapper
│       │   ├── executor.py    # sanctioned thread-pool fallback for pre-3.50 PyGObject (§3)
│       │   └── paths.py       # XDG dirs
│       └── ui/
│           ├── window.py
│           ├── pages/         # one subdir per page: view.py, view_model.py, page.blp
│           └── widgets/
├── helper/
│   ├── lapcare-helper         # the pkexec-invoked script
│   └── dev.lapcare.policy     # polkit policy (per-verb actions)
├── data/                      # .desktop, icons, gschema, metainfo.xml
├── tests/
│   ├── unit/                  # core: pure, fast
│   ├── providers/             # against fixtures + dbusmock
│   ├── fixtures/              # captured real outputs (see §15)
│   └── conftest.py
├── docs/                      # see Agent-first section
└── .github/workflows/
```

Naming: files/modules `snake_case`; one page per directory; provider file named after the tool
it wraps, not the feature it serves (a feature may consume several providers).

## 10. Coding Standards

Full text lives in `STYLEGUIDE.md`; the load-bearing rules:

- **Formatting/lint:** ruff (format + lint), line length 100. Zero warnings policy in CI.
- **Types:** full annotations everywhere; `mypy --strict` for `core/` and `providers/`.
  Frozen `@dataclass` for models. `Protocol` for provider interfaces. No `Any` in signatures
  without a `# why:` comment.
- **Async:** provider I/O is `async def`; core is synchronous and pure. Never block the main
  loop; the subprocess runner enforces timeouts (default 10s) on every external command.
- **Errors:** exceptions from §12 only; never `except Exception: pass`.
- **Docstrings:** every public module/class/function — one summary line plus anything
  non-obvious (units, failure modes, source-format quirks). Providers must document the exact
  sysfs paths / D-Bus interfaces / CLI invocations they touch, with a sample of the raw data.
- **Comments** explain *why* and *constraints* (e.g. "cycle_count reads −1 on some EC firmware"),
  never *what*.
- **No cleverness:** no metaclasses, no monkeypatching outside tests, no dynamic imports, no
  decorators beyond stdlib/GObject ones. Predictable code is agent-editable code.
- **UI:** Blueprint for all layout; stock Adwaita widgets preferred; all user-visible strings
  wrapped for translation (`_()`) from day one.

## 11. Logging Strategy

- Stdlib `logging`, JSON-ish key=value formatting, logger per module
  (`logging.getLogger(__name__)`).
- Runs under the user session → logs go to stderr and are captured by the **systemd journal**
  (`journalctl --user`). No custom log files, no rotation logic — the journal already does this.
  This is the Linux-native choice.
- Levels: `DEBUG` raw provider data summaries; `INFO` lifecycle + user actions; `WARNING`
  degraded states (tool missing, unsupported field); `ERROR` operation failures shown to user.
- `--verbose` CLI flag and `G_MESSAGES_DEBUG`-style env var (`LAPCARE_DEBUG=1`) enable DEBUG.
- **Never log serial numbers, UUIDs, or MACs above DEBUG.** The diagnostic report export, not
  the log, is the sharing mechanism — and it has explicit redaction.
- The helper logs to stderr (captured by pkexec/journal) and never logs command output at
  privileged level beyond exit status.

## 12. Error Handling Strategy

Small, meaningful exception hierarchy in `core`:

```
LapcareError
├── ProviderUnavailable(reason: TOOL_MISSING | UNSUPPORTED_HARDWARE | PERMISSION_DENIED)
├── ProviderTimeout
├── ProviderParseError      # raw payload attached at DEBUG for bug reports
└── PrivilegedActionDenied  # user cancelled/failed polkit auth
```

Rules:
- Providers translate every underlying failure (D-Bus error, `FileNotFoundError`, non-zero
  exit, JSON decode error) into one of these. Nothing above the provider layer ever sees a
  `CalledProcessError`.
- **Absence is data, not an exception**: "no discrete GPU" is an empty list; "can't ask about
  GPUs" is `ProviderUnavailable`.
- View-models map exceptions to the four page states (§7). `PrivilegedActionDenied` is a quiet
  toast, not an error page — declining auth is a legitimate choice.
- Unexpected exceptions: caught at the main-loop boundary, logged with traceback, surfaced as an
  "unexpected error" banner with a "copy details for bug report" button. The app never dies
  because one panel failed.
- Every diagnostic check runs isolated; a crashing check reports itself as `Fail (check error)`
  and the run continues.

## 13. Security Considerations

- **Threat model:** the app handles no network input except fwupd metadata (which fwupd itself
  verifies against LVFS signatures — we never download firmware ourselves). Primary risks are
  (a) privilege-escalation bugs in our helper, (b) command injection into wrapped CLIs,
  (c) leaking identifying data in exports/logs.
- **Subprocess hygiene:** one audited runner; `shell=False` always; argv lists only; absolute
  paths for binaries resolved against a whitelist; environment scrubbed; timeouts mandatory.
- **Parsing hygiene:** treat all tool output (even root-produced) as untrusted input — size
  limits, strict JSON parsing, no `eval`-anything.
- **Helper hardening:** fixed verb set, no user-controlled arguments except a device path that
  is validated (`/dev/sd[a-z]+`, `/dev/nvme\d+(n\d+)?` and must exist as a block device), root
  ownership, `0755`, installed to `/usr/libexec/`.
- **Data at rest:** history DB and settings under XDG dirs with default perms; nothing secret
  is stored. Exports redact identifiers by default; including them is an explicit checkbox.
- **Fixture privacy:** `--capture-fixtures` redacts serials/UUIDs/MACs **at capture time** by
  default; a local-only `--include-identifiers` flag exists for debugging, and unredacted
  captures are never accepted upstream (enforced by the fixture review checklist, §15).
- **Supply chain:** minimal deps (§4), lockfile for dev tooling, Dependabot, and releases built
  in CI from tags — no artifacts built on maintainer laptops.
- fwupd updates are triggered via its D-Bus API, so **fwupd's own polkit policy and LVFS
  signature verification** govern firmware installation. We add no bypasses.

## 14. Privilege Escalation Strategy

**Decision: polkit-native, three tiers. No sudo. No setuid. No root daemon (yet).**

1. **Tier 0 — none needed (most of the app).** UPower, sysfs battery/thermal/DMI reads,
   hwmon, lspci/lsusb are unprivileged. The MVP dashboard works with zero auth prompts.
2. **Tier 1 — delegate to services that already do polkit.** fwupd refreshes/updates go through
   `org.freedesktop.fwupd` D-Bus methods; fwupd's policy decides when to prompt. We inherit
   correct behavior for free.
3. **Tier 2 — our helper via pkexec, one polkit action per verb.**
   `dev.lapcare.smart-report`, `dev.lapcare.nvme-report`, `dev.lapcare.dmi-full`, with
   `allow_active=auth_admin_keep` (active local session may auth; auth cached briefly, so
   scanning two disks isn't two prompts). Policy file ships in the package; each action's
   description explains in plain language what will run. Device targeting uses the
   enumerate-and-match rule (§6). **ADR-0006 — the helper threat model and validation spec
   (device discovery rules, command allowlists, env scrubbing, timeouts, negative tests, and
   the future pkexec→D-Bus-service migration path) — must be accepted before M4 begins.**

Future (post-MVP) writes like battery charge thresholds
(`/sys/class/power_supply/BAT0/charge_control_end_threshold`) get **their own new actions**
(`dev.lapcare.set-charge-threshold`) — never widen an existing one. If write-features
accumulate, revisit as ADR: a small D-Bus **system service** with fine-grained polkit checks is
the correct next step (it's what fwupd/UPower themselves do), replacing pkexec spawns. That's
deliberately deferred — a root daemon is a liability the MVP doesn't need.

UI rule: any control that will trigger an auth prompt is visually marked (lock emblem), and
declining is handled silently (§12).

## 15. Testing Strategy

Test what we own (orchestration, parsing, interpretation, state machines); don't test the
kernel or GTK.

- **Unit tests (`tests/unit/`)** — core layer: wear math, health scoring, every diagnostic
  check, report rendering, redaction. Pure functions, no mocks, milliseconds. Target: core at
  ~100% branch coverage (it's small and pure; this is cheap).
- **Provider tests (`tests/providers/`)** — the crown jewels: a **fixture corpus** of real
  captured data under `tests/fixtures/<source>/<machine>/` — sysfs trees (as directory
  snapshots), `smartctl --json` outputs, fwupd device lists, `/proc/acpi/ibm` files — from real
  ThinkPads (T480, X1 Carbon, P-series…) *and* pathological cases (missing `cycle_count`,
  `charge_full > design`, dual batteries, non-ThinkPad). Providers take a root-path/runner
  parameter so fixtures inject cleanly. D-Bus providers tested against **python-dbusmock**
  (which ships UPower and fwupd templates). Contributors add fixtures via a
  `lapcare --capture-fixtures` dev command — every bug report can become a regression fixture.
  **Fixture governance (must exist before any community capture is accepted, i.e. within M1):**
  a documented fixture schema, capture-time redaction by default (§13), and a maintainer review
  checklist (identifiers scrubbed, machine/kernel recorded, quirk documented in the provider's
  module doc). Fixtures are a privacy surface and a maintenance surface; they get process.
- **View-model tests** — GObject view-models driven with fake providers; assert state
  transitions (loading → ready/unavailable). No display server needed.
- **UI smoke test** — one CI job under `xvfb`/`dbus-run-session`: app launches with all-fake
  providers, each page navigates without criticals. Not screenshot testing.
- **Helper tests** — argument validation and injection attempts (the security-critical surface),
  run unprivileged with the tool runner faked.
- **Manual test matrix** — `docs/testing.md` checklist per release across real hardware
  (maintainer machines + community "hardware testers" recruited via an issue template).

Gate: CI green = lint + mypy + import-linter + unit + provider + view-model + smoke.

## 16. CI/CD Strategy

GitHub Actions, three workflows:

1. **`ci.yml`** — two lanes:
   - *Fast lane* (every PR): ruff → mypy → import-linter → pytest (with dbusmock) → xvfb smoke
     test, on the newest LTS only. Target < 5 min; this is what `./check` mirrors locally.
   - *Full lane* (main, nightly, release tags): the same across the **both-LTS matrix**, plus
     meson build and `dpkg-buildpackage` (artifact retained). Packaging regressions surface
     within a day rather than blocking every PR.
2. **`release.yml`** (on tag `v*`): full CI, build source tarball + .deb, generate release
   notes from CHANGELOG, create GitHub Release, upload to PPA (dput). Releases are built only
   here (§13 supply chain).
3. **`docs.yml`**: link-check docs; fail if `ROADMAP.md` conflicts with declared milestone
   status file (keeps agent-facing status honest).

Branch policy: `main` always releasable; PRs require green CI; squash-merge with conventional
commit subjects (`feat:`, `fix:`, `docs:`, `provider:`) — cheap, greppable history for humans
and agents.

## 17. Release Strategy

- **Cadence:** time-boxed minor releases roughly every 6–8 weeks post-MVP; patch releases as
  needed. SemVer: pre-1.0 during MVP (`0.x`), `1.0` = MVP definition (§20) met and stable on
  two LTS releases.
- **Staged public labels (so 1.0 is not the first time the hard features meet users):**
  every milestone close tags `0.N.0`, and two of those are *announced*: the close of M2 is the
  **public alpha** (read-only, zero privileges — lowest possible risk for first exposure) and
  the close of M3 is the **beta** (firmware updates get a full release cycle of field testing
  before 1.0). All open-source hygiene files (SECURITY.md, code of conduct, issue + hardware-
  tester templates, trademark guidance, fixture contribution policy) must exist **before the
  alpha announcement**.
- **Channels:**
  1. **Ubuntu PPA (.deb)** — primary. The app wants tight system integration (polkit policy in
     `/usr/share/polkit-1`, helper in `/usr/libexec`, host tool access); native packaging is the
     honest fit.
  2. **GitHub Releases** — tarball + .deb for non-PPA users.
  3. **Flatpak — deliberately deferred** (recorded as an ADR): the sandbox blocks arbitrary
     sysfs reads, pkexec helpers, and host binaries (`smartctl`). fwupd/UPower portions would
     work via D-Bus talk permissions, but shipping a half-functional Flatpak damages the product
     promise. Revisit when the privileged D-Bus service (§14 future) exists, since that
     architecture is Flatpak-compatible.
- **Support:** latest release only, pre-1.0. Post-1.0: latest minor + security fixes for the
  previous one.
- **Other distros:** nothing in the code is Ubuntu-specific; install paths are Meson options,
  and `docs/packaging.md` documents them (polkit policy dir, libexecdir, AppStream metainfo,
  uninstall behavior). Fedora/Arch/Debian packaging is explicitly **community-owned** — we
  keep it *possible*, we don't commit to maintaining it.

## 18. Documentation Strategy

Two audiences, two trees:

- **Users:** `README.md` (what/screenshots/install), in-app help, `docs/user/` (FAQ,
  troubleshooting, "which tools do I need for which panel").
- **Contributors & AI agents:** the root guide files + `docs/` (next section). Documentation
  is updated **in the same PR** as the change it describes — CI's docs workflow and the PR
  template both enforce the habit. Every ADR is immutable once accepted; superseding requires a
  new ADR that links back.

Principle: documentation describes *current truth* + *decisions*; it never contains aspirational
content masquerading as fact (that's what `ROADMAP.md` is for). Stale docs are treated as bugs.

## Agent-First Repository Design

### Root guide files

| File | Contents | How agents use it |
|---|---|---|
| **`AGENTS.md`** | The agent entry point, kept under ~150 lines: 10-line project summary; layer diagram; the import rules table (§8); "before you code" checklist (read STYLEGUIDE, check `docs/status/`, find the relevant ADRs); how to run lint/tests/app; a *task-type routing table* ("adding a provider → read `docs/guides/adding-a-provider.md`; UI change → `docs/guides/adding-a-page.md`"); hard prohibitions (no new deps without ADR, no shell=True, no GTK in core, don't edit generated files). | Read **first, every session**. It routes to everything else so the agent never has to guess where truth lives. |
| **`ARCHITECTURE.md`** | One-page version of §3–§8 with the diagram, layer responsibilities, data-flow rule, and links to per-module docs. | Read before any cross-module change; the import table is the contract to preserve. |
| **`CONTRIBUTING.md`** | Workflow (branch → PR → CI), commit conventions, PR template expectations, fixture-capture instructions, definition of done (code + tests + docs + status update). | The agent's definition of "task complete". |
| **`ROADMAP.md`** | Milestones with objectives/acceptance criteria and a status marker per milestone; links to `docs/status/` for fine-grained state. | Tells agents what's in/out of scope *now*, preventing eager implementation of future features. |
| **`DECISIONS.md`** | Index table of ADRs (number, title, status, one-line summary) pointing into `docs/adr/`. | Before proposing a design change, the agent checks whether it was already decided — and if it wants to overturn one, it writes a superseding ADR rather than silently diverging. |
| **`STYLEGUIDE.md`** | §10 in full, plus UI conventions (page states, widget preferences, Blueprint patterns) and naming rules, each with a right/wrong code pair. | Loaded alongside any code-writing task; examples make conventions copyable rather than interpretable. |

### `/docs` structure

```
docs/
├── adr/                    # 0001-app-name.md, 0002-license.md, 0003-gtk4-python.md,
│                           # 0004-polkit-pkexec.md, 0005-flatpak-deferred.md …
│                           # Format: Context / Decision / Consequences / Alternatives
├── modules/                # one page per module: purpose, public API, data sources
│   ├── core.md             # (exact sysfs paths / D-Bus ifaces / CLI invocations),
│   ├── providers.md        # quirks encountered on real hardware, testing approach
│   ├── ui.md
│   └── helper.md
├── guides/                 # step-by-step recipes — the highest-leverage agent docs.
│   │                       # AUTHORING RULE: guides are extracted from the FIRST REAL
│   │                       # implementation (end of M1), never written speculatively —
│   │                       # a recipe with no working example is fiction.
│   ├── adding-a-provider.md    # checklist: port, availability, fixtures, registry,
│   │                           # dbusmock/fixture tests, module doc entry
│   ├── adding-a-page.md        # blueprint + view-model + 4-state pattern + tests
│   ├── adding-a-diagnostic.md
│   └── capturing-fixtures.md
├── status/                 # implementation truth, one file per milestone:
│   ├── m1-hardware-info.md     # checklist of acceptance criteria with done/todo marks,
│   └── ...                     # known gaps, deferred items. Updated in the same PR
│                               # as the work. THIS is where an agent learns what
│                               # exists vs. what's aspirational.
├── user/                   # FAQ, troubleshooting, per-panel tool requirements
└── testing.md              # test taxonomy + manual hardware test matrix
```

Why this works for agents: **status is separated from intent** (status/ vs ROADMAP), **decisions
are discoverable and dated** (adr/), **conventions come with examples** (STYLEGUIDE, guides/),
and **every extension point has a recipe** (guides/). An agent session's ideal read set —
AGENTS.md → relevant guide → relevant module doc → relevant status file — is ~4 short documents,
not a repo-wide crawl.

## Development Workflow (Milestone-Based)

Rhythm per milestone:

1. **Open** — milestone doc created in `docs/status/mN-….md` from ROADMAP's objective +
   acceptance criteria; broken into issues sized to one PR each.
2. **Implement** — each PR = code + tests + docs + status-file tick, green CI, review against
   STYLEGUIDE. Agents and humans follow the identical loop.
3. **Verify** — all acceptance criteria checked on ≥ 2 real ThinkPad models (manual matrix);
   any deferred item is written into the status file explicitly.
4. **Close** — ROADMAP status flipped, CHANGELOG updated, tagged pre-release (`0.N.0`),
   retrospective notes (what fixture gaps / doc gaps were found) appended to the status file.

Nothing from milestone N+1 starts before N's acceptance criteria are met or explicitly re-scoped
in ROADMAP (small ADR if the change is architectural).

## 19. Roadmap — Milestones

**M0 — Skeleton & Rails (the agent-readiness milestone)**
*Objective:* empty-but-running app plus all rails: repo layout, Meson build, CI (both lanes),
lint/mypy/import-linter, window with sidebar and one placeholder page, logging, `./run` +
`./check` wrappers — plus a **stack-validation spike**: prove GTK4 + libadwaita + Blueprint +
PyGObject-asyncio (or the platform executor fallback, §3) + Meson + dbusmock end-to-end on
*each* supported Ubuntu LTS before any feature code.
*Acceptance:* `./run` opens a window and `./check` passes on both LTS releases; the chosen
async mechanism per LTS is recorded in ADR-0007; CI green.
*Tests:* smoke test in CI.
*Docs:* **contracts only** — AGENTS.md, ARCHITECTURE.md, STYLEGUIDE.md, CONTRIBUTING.md,
ROADMAP.md, and ADRs for decisions actually made (0001 name, 0002 license, 0003 GTK4/Python,
0004 polkit strategy, 0005 Flatpak deferred, 0007 async-per-LTS). `docs/guides/` recipes are
deliberately NOT written yet — they are extracted from the first real implementations at the
end of M1, so they document reality rather than speculation.

**M1 — System Overview & Hardware Information**
*Objective:* Dashboard page (model, BIOS version, kernel, uptime, quick stats) + Hardware page
(DMI identity, CPU/memory summary, PCI/USB inventory). Providers: `dmi`, `os_info`, `pci_usb`,
`thinkpad_acpi` (detection only). ThinkPad detection banner for unsupported machines.
*Acceptance:* correct data on 2+ real ThinkPads; non-ThinkPad shows graceful banner; every
panel handles `unavailable`; **fixture governance in place** (schema, capture-time redaction,
review checklist) before the first community capture is merged.
*Tests:* fixture corpus started (≥ 2 machines); provider + view-model tests.
*Docs:* module docs for shipped providers; status file complete; `docs/guides/` recipes
extracted from the real providers/pages built here.

**M2 — Battery Health & Wear Analysis**
*Objective:* Battery page — live status via UPower, wear analysis via sysfs
(`charge_full[_design]`, `cycle_count`), health classification, daily snapshot history +
wear-over-time chart, dual-battery support.
*Acceptance:* wear % matches manual sysfs math on test machines; missing `cycle_count` handled;
history survives restarts. **Milestone close = tagged `0.3.0` and announced as the public
alpha** — all open-source hygiene files (§17) must exist first.
*Tests:* wear/scoring unit tests incl. pathological fixtures; dbusmock UPower tests.

**M3 — Firmware Updates (fwupd/LVFS)**
*Objective:* Firmware page — device list, current vs. available versions, release notes,
refresh metadata, trigger updates via fwupd D-Bus (its polkit governs), reboot-required and
progress states.
*Acceptance:* full update flow verified on real hardware against LVFS; failure paths (no
network, fwupd absent, update declined) all render correctly. **UX acceptance criteria:**
reboot-required flow is unambiguous; update failure shows a recovery path; AC/battery
preconditions (enforced by fwupd) are surfaced *before* the user commits; post-update
"what changed" is shown; declining auth is silent, not an error. Milestone close = **beta**
announcement.
*Tests:* dbusmock fwupd template covering device/release/progress signals.

**M4 — Storage Health, Diagnostics & Report Export**
*Entry gate:* **ADR-0006 (helper threat model & validation spec, §14) accepted, and
SECURITY.md published.** No helper code before the ADR.
*Objective:* privileged helper + polkit policy ship; Storage page (SMART/NVMe health);
Diagnostics page (check engine + initial checks: battery wear, SMART, firmware currency,
thermal sanity, disk space); health score on Dashboard; export report (MD/HTML/JSON) with
redaction toggle.
*Acceptance:* SMART data after a single polkit prompt; declining auth degrades gracefully;
diagnostics complete < 10 s; exported report opens correctly and redacts by default; health
score displays per-signal confidence and is labeled experimental (§6).
*Tests:* helper negative/injection test suite per ADR-0006; every check unit-tested; report
snapshot tests.

**M5 — MVP Hardening & Release (v1.0)**
*Objective:* polish (empty/error-state copy with remediation, strings/i18n scaffolding), perf,
PPA pipeline live, user docs, community hardware-test round across ≥ 5 ThinkPad models; review
health-score calibration against the fixture corpus (§6).
*Acceptance:* MVP definition (§20) fully met; zero known crashers; install-from-PPA works on
supported LTS releases. **Accessibility criteria (concrete, not "a11y pass"):** every page
fully keyboard-navigable; all rows/values expose screen-reader labels; no information conveyed
by color alone; respects system font scaling. **Performance criterion:** < 1.5 s from launch to
window + first meaningful dashboard content (progressive startup, §7) on a mid-range ThinkPad.

## 20. MVP Definition

A user on Ubuntu LTS with a ThinkPad can install LapCare from a PPA and:

1. See system overview and full hardware information — no terminal, no prompts.
2. See battery status, health classification, wear %, cycle count, and wear history.
3. See, refresh, and install firmware updates via fwupd/LVFS with correct progress/reboot flows.
4. See storage SMART/NVMe health after a single polkit authentication.
5. Run one-click diagnostics and see a scored health dashboard with explainable results.
6. Export a redacted-by-default diagnostic report (Markdown/HTML/JSON).
7. Every feature degrades gracefully on missing tools, unsupported hardware, or denied auth.

Explicitly **not** in MVP: any hardware *writes* (charge thresholds, always-on USB), thermal/fan
live monitoring pages, notifications, scheduling, tray/background presence, non-ThinkPad
support guarantees, Flatpak.

Note on staging: 1.0 is *not* the first public exposure of this feature set — the read-only
portion ships as a public alpha after M2 and firmware updates get a full beta cycle after M3
(§17), so each high-risk feature meets users one release before the 1.0 label.

## 21. Future Roadmap (post-1.0, order tentative)

- **M6 — Battery charge thresholds:** first write operation; new polkit action; triggers two
  ADRs deliberately deferred from the MVP: the privileged D-Bus system service, and the
  capability model (`supports_battery_thresholds`, …) that generalizes `availability()` (§6).
- **M7 — Thermal & fan monitoring:** hwmon live charts; thinkpad_acpi fan RPM; (fan *control*
  much later, if ever — safety-sensitive).
- **M8 — Notifications & scheduling:** firmware-update and battery-degradation notifications
  via XDG Notification portal; systemd user timers (not cron, not an in-app daemon) for
  scheduled health checks.
- **M9 — ThinkPad extras:** always-on USB, keyboard backlight, mic/camera privacy state —
  each via thinkpad_acpi/sysfs with its own polkit action if it writes.
- **M10 — Broader hardware:** provider registry gains vendor quirk layers (Dell, Framework —
  Framework especially, given its sysfs-friendly firmware culture); capability-model ADR if M6
  hasn't already forced it; rename/rebrand decision.
- **M11 — Flatpak**, once the D-Bus service architecture makes sandboxing honest.

## 22. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Hardware variance: sysfs/ACPI fields differ or lie across ThinkPad generations | High | Medium | Fixture corpus from real machines; `availability()` contract; every field optional in models; community fixture-capture command; bug→fixture pipeline |
| 2 | Trademark exposure ("Lenovo", "ThinkPad", "Vantage") | Medium | High | Neutral name (ADR-0001); "for ThinkPads" only descriptively; no Lenovo logos/assets |
| 3 | Privileged-helper vulnerability | Low | Critical | Tiny fixed-verb helper, no free-form args, injection test suite, per-verb polkit actions, security review before M4 ships |
| 4 | Upstream drift (fwupd API, sysfs paths, tool JSON schemas) | Medium | Medium | All source knowledge isolated in one provider each; CI on newest LTS catches drift early; version-gated code paths documented in module docs |
| 5 | Scope creep toward reimplementing tools ("just parse the EC directly…") | Medium | High | Guiding principle #1 enforced in review; new data sources require an ADR naming the wrapped tool |
| 6 | Solo-maintainer bus factor / burnout | Medium | High | The entire agent-first design doubles as new-human-contributor onboarding; small milestones; strict scope discipline |
| 7 | GNOME/libadwaita API churn | Low | Low | Target stable libadwaita in current LTS; stock widgets only; CI matrix catches breakage |
| 8 | Flatpak-first user expectations | Medium | Low | README explains why native packaging (ADR-0005); Flatpak on public roadmap |
| 9 | Health score perceived as arbitrary or alarmist | Medium | Medium | Fully explainable rubric shown in UI; conservative thresholds; "what does this mean" links |
| 10 | Ubuntu-only tunnel vision limits adoption | Low | Medium | Nothing Ubuntu-specific in code (Debian-family packaging only); distro-specific bits confined to packaging dir; install paths as Meson options; `docs/packaging.md` |
| 11 | PyGObject/GLib version skew across LTS breaks the asyncio integration (`gi.events` needs ≥ 3.50; Ubuntu 24.04 ships 3.48) | High | Medium | M0 stack-validation spike per LTS; sanctioned platform-owned executor fallback (§3); async mechanism per LTS recorded in ADR-0007 |
| 12 | Fixture corpus leaks identifying data or rots without process | Medium | Medium | Capture-time redaction by default (§13); fixture schema + review checklist gate community captures (§15) |

---

*Next step when implementation begins: execute M0 exactly as specified — rails and docs before
features.*
