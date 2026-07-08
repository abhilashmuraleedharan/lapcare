# Guide: Adding a Provider

Extracted from the real M1 providers. Reference implementations: sysfs-based →
`src/lapcare/providers/dmi.py`; command-based → `src/lapcare/providers/pci_usb.py`;
port-composing → `src/lapcare/providers/thinkpad_acpi.py`; raw D-Bus →
`src/lapcare/providers/upower.py`; GObject-Introspection library over D-Bus →
`src/lapcare/providers/fwupd.py` (tested against a local dbusmock template under
`tests/dbusmock_templates/` when python-dbusmock ships none; D-Bus test classes share ONE
session-wide private system bus — see `tests/providers/conftest.py`).

A provider is the ONE module that knows a data source's paths, formats, and quirks.
Checklist:

1. **Models** (`core/models.py`): frozen dataclass(es), every field `Optional` unless the
   fixture corpus proves it universal. Absence of hardware is data (None/empty list);
   inability to ask is an exception.
2. **Port** (`core/ports.py`): a `Protocol` with cheap synchronous `availability()` and
   `async` read methods returning core models. Ports raise only `core.errors`.
3. **Provider module** (`providers/<tool>.py`, named after the source, not the feature):
   - Concrete class named `<Topic><Transport>` (e.g. `DmiSysfs`, `PciUsbTools`).
   - Constructor takes the injection seam: `root: Path = Path("/")` for filesystem sources,
     `runner: ToolRunner = run_tool` for command sources. Never both jobs in one class
     without reason.
   - Module docstring documents the EXACT files/invocations read, sample values, and
     kernel/interface stability notes + known model quirks. This is a hard STYLEGUIDE rule.
   - Filesystem reads go through `platform.files.read_str/read_int` (bounded, None on
     unreadable). Commands go through the audited runner — add the binary to
     `ALLOWED_TOOLS` in `platform/subprocess.py` (a reviewed, conscious act) and translate
     its exceptions at the boundary:
     `ToolNotFound → ProviderUnavailable(TOOL_MISSING, tool=<package>)`,
     `ToolTimeout → ProviderTimeout`, `ToolFailed → ProviderParseError`.
   - Malformed lines: skip with a DEBUG log; zero parseable output from non-empty text →
     `ProviderParseError`. Never log raw payloads above DEBUG.
4. **Fixtures** (`tests/fixtures/<source>/<machine>/`): at least one real capture
   (`lapcare --capture-fixtures`) and one pathological/synthetic case. Schema:
   `docs/testing.md`.
5. **Tests** (`tests/providers/test_<tool>.py`): happy path against the real capture,
   degradation paths, every error translation. Use `fixture_root()` from
   `tests/providers/conftest.py`; fake runners for command sources.
6. **Wire it** in the composition root (`app.py`) only. The UI never names your class.
7. **Docs**: add your source's section to `docs/modules/providers.md`; if new system
   packages are needed, update `tools/install-deps.sh` AND `debian/control`.
8. **DoD**: `./check --lts 24.04` and `--lts 26.04` green; smoke passes; milestone status
   file ticked.
