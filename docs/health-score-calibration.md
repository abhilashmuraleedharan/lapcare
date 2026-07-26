# Health-Score Calibration Review

The ROADMAP M5 review of every threshold behind the diagnostics verdicts and the
aggregate score: what each number is, where it came from, and how it gets revised.
Code of record: `core/diagnostics.py` (checks + score), `core/battery_analysis.py`
(wear rubric). Change-control rule: thresholds are named constants revised through
this document; **per-check score weights require an ADR** (explainability is a
constitution invariant — a weighted score stops being explainable in one sentence).

## The aggregate

`score = round(100 × mean(OK→1, WARNING→0.5, CRITICAL→0))` over **measured** checks;
SKIPPED checks reduce the reported coverage ("based on N of 5 signals"), never the
score. The UI labels it *experimental* everywhere it appears. This is deliberately the
dumbest defensible aggregate: any user can recompute it from the Diagnostics page.

## Per-signal thresholds and provenance

| Signal | Verdict thresholds | Provenance / confidence rationale |
|---|---|---|
| Battery wear | GOOD < 15 % ≤ FAIR < 30 % ≤ POOR (worst battery counts) | `battery_analysis` rubric, set at M2 from common industry guidance (80 % design capacity ≈ end-of-life ⇒ 30 % wear is unambiguously poor; 15 % keeps GOOD honest for 1-2-year-old machines). HIGH confidence: direct sysfs arithmetic. |
| Storage health | CRITICAL: any `passed=false`. WARNING: pending sectors > 0, or NVMe `percentage_used ≥ 80` | `smart_status.passed` is the drive's own verdict (HIGH confidence; MEDIUM when a drive reports no verdict). Pending sectors are the classic pre-failure signal. 80 % endurance leaves real margin before the drive's rated 100 %. |
| Firmware currency | CRITICAL: any pending update with `urgency=critical`. WARNING: any pending update | LVFS's own urgency taxonomy. MEDIUM confidence always: "no pending updates" is only as fresh as the last metadata refresh. |
| Thermal sanity | CRITICAL ≥ 95 °C, WARNING ≥ 85 °C, on the hottest **plausible** sensor (1 °C < t < 119 °C) | Intel/AMD mobile Tjmax is typically 100-105 °C; sustained ≥ 95 °C at scan time means throttling territory. The plausibility band exists because the E16's EC exposes unpopulated slots reading 2-13 °C (fixture-backed). MEDIUM confidence: hwmon coverage varies by model. |
| Disk space | CRITICAL < 5 % free, WARNING < 10 % free (worst real mount) | Classic operational rule of thumb; below ~5 % many filesystems fragment badly and updates start failing. HIGH confidence: statvfs arithmetic. |

## Known limitations (accepted for 1.0)

- The score treats signals as equally important; a CRITICAL battery and a CRITICAL
  disk cost the same. Defensible only because the per-check verdicts are always shown
  alongside — the score is a pointer, not a diagnosis.
- Thermal is a point-in-time reading: a scan during a compile spike can WARN on a
  healthy machine. The evidence row names the hottest sensor so the user can judge.
- Firmware currency conflates "update exists" with "machine unhealthy" — a
  security-motivated choice (stale firmware is a risk), but it caps healthy-but-
  unrefreshed machines at WARNING.

## What the beta collects (field-data wishlist)

From bug reports and fixture contributions (`docs/guides/capturing-fixtures.md`), the
calibration review wants:

1. SMART captures from **failing and failed drives** (SATA especially — the corpus has
   only one synthetic SATA case) → validates the pending-sectors and endurance bars.
2. Wear + cycle-count pairs from old batteries (> 500 cycles) → tests whether the
   15/30 % rubric matches user-perceived battery quality.
3. hwmon captures from T/X/P-series ThinkPads → hardens the plausibility band and the
   85/95 °C bars against different EC layouts (the community hardware round feeds this).
4. Reports where the user *disagrees* with a verdict — each becomes a fixture and a
   threshold discussion here.

## Revision procedure (post-1.0)

1. Propose the new threshold in a PR editing the constant **and this table**, citing
   the fixtures/reports that motivated it.
2. Existing diagnostics tests pin every verdict boundary — the PR must move the tests
   with the constants, making the change visible in review.
3. Score *structure* changes (weights, non-linear aggregation, new statuses) are an
   ADR, not a threshold revision.
