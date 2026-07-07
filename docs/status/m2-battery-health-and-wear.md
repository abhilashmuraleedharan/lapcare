# M2 — Battery Health & Wear Analysis: Status

**State:** in progress. **Branch:** `feature/m2` (single milestone PR, rebase-merged).
**Objective (ROADMAP):** Battery page — live status via UPower, wear analysis via sysfs,
health classification, daily snapshot history + wear-over-time chart, dual-battery
support. **Close = tag `v0.3.0` and the PUBLIC ALPHA release.**

**Reference hardware probe (E16 Gen 2, 2026-07-07):** BAT0 reports **energy_*** (µWh),
NOT charge_*: energy_full 54,290,000 / design 57,000,000 → wear 4.75%; cycle_count 92;
status `"Not charging"` at 79% (threshold-managed); `ucsi-source-psy-USBC*` supplies must
be filtered by `type`; power_now=0 when not charging.

## Commit plan

- [x] C1 `docs: open milestone M2` — status file + real E16 battery fixture + synthetic
      fixtures (charge_* units, full>design, cycle_count=-1, dual battery, USB entries).
- [x] C2 `feat(core): battery models, wear analysis, health classification, ports` —
      BatteryWear/BatteryStatus/WearSnapshot models, wear math (clamped), HealthClass
      thresholds (documented), BatteryWearProvider/BatteryStatusProvider/HistoryStore
      ports; pathological unit tests.
- [x] C3 `provider: battery_sysfs` — /sys/class/power_supply walk, type filter,
      energy_/charge_ unit handling, quirk tolerance; fixture tests.
- [x] C4 `feat(platform): D-Bus helpers + provider: upower` — platform/dbus.py,
      UPower live status + change signals; python-dbusmock tests.
- [ ] C5 `feat(platform): SQLite HistoryStore` — daily wear snapshots under XDG data dir,
      idempotent per (date, battery), survives restart; tests.
- [ ] C6 `feat(ui): Battery page` — live status group (per battery), health group
      (wear %, class, cycles, capacities), wear-over-time chart (cairo DrawingArea),
      per-panel degradation (UPower absent ≠ dead page), snapshot recording on load;
      VM tests; smoke extended.
- [ ] C7 `feat: capture tool learns battery files` + docs (module docs quirk entries).
- [ ] C8 `docs: close milestone M2; release v0.3.0 (PUBLIC ALPHA)` — version bumps,
      CHANGELOG, ROADMAP flip, merge, tag, GitHub pre-release with .deb artifacts.

## Acceptance criteria (from ROADMAP)

- [ ] Wear % matches manual sysfs math on the E16 Gen 2 (54.29/57.0 → 4.75%)
- [x] Missing/-1 `cycle_count` handled; `charge_full > design` clamped, recorded as quirk
- [x] Both energy_* and charge_* unit families supported (fixtures for each)
- [x] Dual-battery support (fixture-tested)
- [ ] Live status via UPower with change signals; page degrades per-panel when UPower
      is unavailable (wear data still shows)
- [ ] History survives restarts (reopen test); daily snapshot idempotent
- [ ] Wear-over-time chart renders (smoke: zero criticals)
- [ ] ./check + smoke green both LTS; full lane green at close
- [ ] Tag `v0.3.0`; GitHub pre-release published (public alpha); CHANGELOG; ROADMAP

## Known deferrals / notes

_(filled as they arise)_

## Retrospective (filled at close)

_TBD._
