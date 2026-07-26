# Lapcare User Guide

Lapcare shows you everything your ThinkPad can tell you — hardware details, battery
health, firmware updates, storage health, and one-click diagnostics — in one window.
It works on other laptops too, with a note about reduced ThinkPad-specific coverage.

## Installing

**Supported:** Ubuntu 24.04 LTS and 26.04 LTS (and derivatives with the same GNOME
platform versions).

From a GitHub release (until the PPA is live):

```sh
sudo apt install ./lapcare_<version>_all-ubuntu-24.04.deb   # or -ubuntu-26.04.deb
```

From the PPA (once announced — see the README for status):

```sh
sudo add-apt-repository ppa:<owner>/lapcare
sudo apt install lapcare
```

Recommended companions (installed automatically unless you opt out): `fwupd` (firmware
updates), `upower` (live battery status), `smartmontools` (storage health).

## The pages

### Dashboard

Model, BIOS version, OS, kernel, uptime — and an **experimental health score**. The score
is a plain average over the health signals Lapcare can measure without asking for any
authorization; the subtitle tells you how many of the five signals it is based on. Treat
it as a pointer toward the Diagnostics page, not a verdict.

### Battery

Live charge status (via UPower), wear analysis (how much capacity the battery has lost
against its design capacity), a health classification, cycle count, and a wear-over-time
chart that grows one point per day of use. Dual-battery machines show both.

The classification thresholds are deliberately simple: below 15 % wear is *Good*,
15–30 % is *Fair*, above 30 % is *Poor*.

### Hardware

DMI identity (family, machine type, board, BIOS), CPU and memory summary, and the full
PCI/USB inventory.

### Firmware

Every device fwupd manages, its current firmware version, and any available updates from
LVFS with release notes and urgency. "Check for Updates" refreshes the metadata.

Installing an update is performed **by fwupd, not by Lapcare** — fwupd's own
authorization prompt and signature verification govern it. Before committing, Lapcare
checks fwupd's battery precondition and tells you up front if the charge is too low.
During the update you get live progress; afterwards, a summary of what changed and — if
the device needs it — an unmissable "restart to finish" banner.

### Storage

Your physical disks (model, size, type) are listed immediately, with no prompts. Click
**Read Health** to fetch SMART/NVMe health — temperature, wear/endurance, error
counters, and an overall verdict. A failing drive is flagged with *"FAILING — back up
your data now"*; take that literally.

### Diagnostics

One click runs five checks: battery wear, storage health, firmware currency,
temperatures, and disk space. Each check shows its verdict, the evidence it used, and a
confidence tag; a check that could not run says so honestly ("Not measured") instead of
guessing. **Export…** saves the results as Markdown, HTML, or JSON.

## About the authorization prompts

Lapcare asks for your password in exactly two situations, both marked with a lock emblem
on the button:

- **Installing firmware** — the prompt comes from fwupd's own policy.
- **Reading storage health** ("Read Health" or "Run Diagnostics") — reading SMART data
  from a disk requires root. Lapcare uses a tiny, single-purpose, read-only helper for
  this; its design and threat model are public (`docs/adr/0006-…`). One authorization
  covers all your disks and a follow-up diagnostics run within a few minutes.

Declining a prompt is always safe: the action is quietly cancelled and everything else
keeps working. Lapcare never asks at startup, and never writes to your hardware itself.

## Privacy

- Exported reports **exclude identifiers** (serial numbers and the like) — there is no
  option to include them, by design.
- Nothing leaves your machine: Lapcare has no telemetry, no accounts, no network access
  of its own (firmware metadata is fetched by fwupd from LVFS).
- The wear history lives in a small local database under your XDG data directory
  (`~/.local/share/lapcare/`).

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Firmware page says it needs fwupd | `sudo apt install fwupd` |
| Storage health says it needs smartmontools | `sudo apt install smartmontools` |
| Storage health unavailable in a dev/source build | The privileged helper only exists in the installed package — expected |
| Battery page shows no live status | `sudo apt install upower` (wear analysis still works without it) |
| "This doesn't appear to be a ThinkPad" banner | Informational — everything except ThinkPad-specific data still works |
| A page shows "Could not read…" | Run `lapcare --verbose` from a terminal and include the output in a bug report |

Bug reports and hardware quirks: <https://github.com/abhilashmuraleedharan/lapcare/issues>.
Hardware data contributions (redacted by default) are especially welcome — see
`docs/guides/capturing-fixtures.md`.
