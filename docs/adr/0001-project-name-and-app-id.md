# ADR-0001: Project name "Lapcare" and application ID

- **Status:** Accepted
- **Date:** 2026-07-06
- **Deciders:** Project owner (abhilashmuraleedharan), Lead Architect

## Context

The product needs a name and a reverse-DNS application ID. "Lenovo", "ThinkPad", and
"Vantage" are Lenovo trademarks and must not appear in the product name; descriptive use
("for ThinkPads") is acceptable. The application ID is embedded in the `.desktop` file,
AppStream metainfo, GSettings schema, D-Bus name, and future polkit action names — polkit
action names in particular are painful to migrate after users have granted them, so this
decision must be made before any of those files exist. Using a `dev.lapcare.*` /
`app.lapcare.*` style ID requires owning the corresponding domain; the GNOME-sanctioned
alternative for projects hosted on GitHub without a domain is `io.github.<owner>.<name>`.

## Decision

We will name the application **Lapcare** (repository and binary: `lapcare`) and use the
application ID **`io.github.abhilashmuraleedharan.lapcare`** for the desktop file, metainfo,
GSettings schema, D-Bus name, and as the prefix for all polkit actions
(`io.github.abhilashmuraleedharan.lapcare.<verb>`).

## Consequences

- No trademark exposure in naming; "ThinkPad" appears only descriptively.
- No domain purchase or renewal risk; the ID is valid for Flathub if/when Flatpak arrives
  (ADR-0005).
- The ID is long; this is cosmetic and affects developers only.
- A future rebrand (contemplated around M10 if hardware scope broadens) would change the
  visible name cheaply, but migrating the app ID and polkit actions would need a dedicated
  migration plan — we accept that cost as unlikely to be paid.

## Alternatives Considered

- **`dev.lapcare.Lapcare`** (assumed in early planning): rejected — requires owning
  `lapcare.dev` indefinitely; a lapsed domain under someone else's control next to our polkit
  action names is an unacceptable tail risk for zero user-visible benefit.
- **Names containing "ThinkPad"/"Vantage"** (e.g. `thinkpad-companion`, `openvantage`):
  rejected on trademark grounds.
