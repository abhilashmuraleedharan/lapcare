# Architecture Decision Records — Index

ADRs live in `docs/adr/`, follow `docs/adr/template.md`, and are **immutable once accepted**:
to change a decision, write a new ADR that supersedes the old one. Before proposing a design
change, check this index — if the topic is decided, your change needs a superseding ADR, not
a silent divergence.

| ADR | Title | Status | One-line summary |
|---|---|---|---|
| [0001](docs/adr/0001-project-name-and-app-id.md) | Project name and app ID | Accepted | "Lapcare"; app id `io.github.abhilashmuraleedharan.lapcare`; trademarks only descriptive |
| [0002](docs/adr/0002-license-gpl-3.0-or-later.md) | License | Accepted | GPL-3.0-or-later; SPDX headers; DCO sign-off, no CLA |
| [0003](docs/adr/0003-ui-stack-gtk4-libadwaita-python.md) | UI stack | Accepted | GTK4 + libadwaita via PyGObject, Blueprint layouts; GNOME-first, no toolkit abstraction |
| [0004](docs/adr/0004-privilege-strategy-polkit.md) | Privilege strategy | Accepted | Three polkit tiers; fixed-verb pkexec helper with enumerate-and-match; no root daemon |
| [0005](docs/adr/0005-packaging-deb-first-flatpak-deferred.md) | Packaging | Accepted | Native .deb/PPA first; Flatpak deferred until the D-Bus service exists |
| [0006](docs/adr/0006-privileged-helper-threat-model.md) | Privileged-helper threat model & validation spec | Accepted | One stdlib-only pkexec helper, per-verb polkit actions via `exec.argv1`; enumerate-and-match; M4 ships `smart-report` only; injection suite is part of DoD |
| [0007](docs/adr/0007-async-integration-per-lts.md) | Async integration per Ubuntu LTS | Accepted | Native `gi.events` on 26.04+; dedicated background asyncio loop thread + `GLib.idle_add` on 24.04; one scheduler interface |
| [0008](docs/adr/0008-capability-model-deferred.md) | Capability model | Accepted | Deferred; `availability()` is the seed; ADR triggered by first write feature (M6) or second vendor (M10) |
| [0009](docs/adr/0009-firmware-transport-libfwupd-gir.md) | Firmware transport | Accepted | `Fwupd.Client` (GObject Introspection over libfwupd), not raw D-Bus; fwupd owns download/verify/fd-passing; new runtime dep `gir1.2-fwupd-2.0` |
