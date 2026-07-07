# ADR-0004: Privilege strategy — polkit-native, three tiers, no root daemon

- **Status:** Accepted
- **Date:** 2026-07-06
- **Deciders:** Project owner, Lead Architect (reconciled with Principal Engineer review)

## Context

Most of Lapcare needs no privileges: UPower, battery/thermal/DMI sysfs, hwmon, and PCI/USB
inventory are world-readable. Firmware operations are performed by fwupd, which enforces its
own polkit policy and LVFS signature verification. Only SMART/NVMe reads (and a few root-only
DMI fields) need elevation in the MVP. The MVP is read-only by constitution. A resident root
service would be the largest security liability the project could add.

## Decision

We will use a three-tier, polkit-native model:

1. **Tier 0 — no privileges** for everything that doesn't need them (most of the app).
2. **Tier 1 — delegate** to system services that already do polkit (fwupd via
   `org.freedesktop.fwupd`); we inherit their prompting and verification, and add no bypasses.
3. **Tier 2 — a short-lived, fixed-verb helper** (`/usr/libexec/lapcare/lapcare-helper`)
   invoked via `pkexec`, one polkit action per verb
   (`io.github.abhilashmuraleedharan.lapcare.smart-report`, `.nvme-report`, `.dmi-full`),
   `allow_active=auth_admin_keep`. Device targeting is **enumerate-and-match**: the helper
   accepts a bare device name (e.g. `nvme0n1`), enumerates `/sys/block` itself, and refuses
   anything not in that set — it never accepts paths, so there is no path/symlink/regex
   validation surface. No free-form arguments, no user-controlled config, no state.

**No `sudo`, no setuid, no root daemon.** Future *write* features (first: battery charge
thresholds, M6) each get their own new polkit action — never a widened existing one — and the
first write feature triggers an ADR evaluating a small privileged D-Bus system service (the
UPower/fwupd pattern) to replace pkexec spawns.

UI rule: any control that will trigger an auth prompt is visually marked; declining auth is a
quiet degradation, never an error page.

## Consequences

- MVP dashboard works with zero auth prompts; the privileged surface is three read-only verbs.
- `auth_admin_keep` means scanning two disks isn't two prompts.
- The helper's verb schema must be designed as a future D-Bus method schema so a later service
  migration doesn't get harder (requirement on ADR-0006).
- **ADR-0006 (helper threat model and validation spec) is a blocking entry gate for milestone
  M4** — no helper code before it is accepted. SECURITY.md must be published by then (done in
  M0).
- Flatpak remains blocked until the D-Bus service exists (see ADR-0005).

## Alternatives Considered

- **Privileged D-Bus system service now:** rejected — a resident root process to serve three
  read-only calls inverts the risk/benefit; deferred to the first write feature. (Principal
  Engineer review suggested considering it earlier; rejected in reconciliation, see
  `docs/history/2026-07-architecture-review-reconciliation.md` R4.)
- **sudo / setuid helper:** rejected — no per-action granularity, no desktop auth integration,
  setuid is an audit nightmare.
- **Path-validation of user-supplied device paths:** rejected — regex/symlink validation of
  untrusted paths is exactly the bug class the enumerate-and-match design eliminates.
