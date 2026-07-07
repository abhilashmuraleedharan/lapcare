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
| 0006 | Privileged-helper threat model & validation spec | **Reserved** | Must be written and accepted before milestone M4 begins (blocking entry gate) |
| 0007 | Async integration per Ubuntu LTS | **Reserved** | Written during the M0 stack-validation spike (Commit 9); records `gi.events` vs executor fallback per LTS |
| [0008](docs/adr/0008-capability-model-deferred.md) | Capability model | Accepted | Deferred; `availability()` is the seed; ADR triggered by first write feature (M6) or second vendor (M10) |
