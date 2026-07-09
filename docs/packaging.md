# Packaging Lapcare

Everything a distribution packager needs. Debian/Ubuntu packaging is maintained in-tree
(`debian/`); other formats are community-owned — this file is the contract.

## Build system

Meson (≥ 1.3) + ninja. Python ≥ 3.12 is a hard floor (checked at configure time,
ADR-0003). Build deps: `meson`, `blueprint-compiler`, `python3`, `libglib2.0-dev-bin`
(glib-compile-resources/schemas), `desktop-file-utils`, `appstream`, `gettext`.

```sh
meson setup build --prefix=/usr
meson compile -C build
meson install -C build --destdir "$DESTDIR"
```

## What gets installed where

| Artifact | Path (fixed by Meson options) |
|---|---|
| Python package | `python3 site-packages/lapcare/` |
| Launcher | `bindir/lapcare` (generated; embeds pythondir + pkgdatadir) |
| GResource bundle | `datadir/lapcare/lapcare.gresource` |
| Desktop entry / AppStream / GSettings schema | standard `datadir` locations |
| **Privileged helper** | `libexecdir/lapcare/lapcare-helper` (0755, root-owned) |
| **Polkit policy** | `datadir/polkit-1/actions/io.github.….lapcare.policy` |

**libexecdir warning:** the polkit policy's `exec.path` annotation and the client
(`providers/storage_smart.py:HELPER_PATH`) both reference the **canonical path**
`/usr/libexec/lapcare/lapcare-helper`. If your distro relocates libexecdir, you must
patch all three in lockstep or the polkit action match (and therefore per-verb
authorization) silently degrades to polkit's generic exec action. Debian compat ≥ 12
keeps meson's `/usr/libexec` default — no patch needed there.

## Runtime dependencies

Hard: `python3 (>= 3.12)`, `python3-gi (>= 3.48)`, `python3-gi-cairo`, `gir1.2-gtk-4.0`,
`gir1.2-adw-1 (>= 1.4)`, `gir1.2-fwupd-2.0`, `pciutils`, `usbutils`, `pkexec`.
Recommended (graceful degradation without): `fwupd`, `upower`, `smartmontools`.
There are **no** pip/PyPI dependencies — distro packages only (constitution invariant).

## Security-relevant packaging rules

- The helper must be root-owned, mode 0755, **never** setuid. It is only useful through
  pkexec + the shipped polkit policy (threat model: `docs/adr/0006-…`).
- Removing the package must remove the helper and the polkit policy together (a policy
  pointing at a missing path is inert but confusing; the Debian packaging handles this
  automatically since both are plain package files).
- Do not patch the helper. Its argument validation, tool path, and timeouts are part of
  a reviewed threat model; downstream deltas void the audit.
- Release artifacts should be built in CI from tags, not on personal machines
  (`docs/security-design.md`, supply-chain rules).

## Tests

`./check` (ruff + mypy + import-linter + pytest) needs the dev requirements
(`requirements-dev.txt`) and runs headless. The GUI smoke test needs `xvfb` and a built
gresource: see `tests/smoke/test_launch.py`'s docstring for the exact invocation.
The helper's injection suite (`tests/helper/`) runs unprivileged by design.

## AppStream / desktop integration

App ID `io.github.abhilashmuraleedharan.lapcare` everywhere (desktop file, metainfo,
gschema, D-Bus-free). `appstreamcli validate` and `desktop-file-validate` run as meson
tests when the tools are present.
