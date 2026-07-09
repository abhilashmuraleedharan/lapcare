# Guide: Adding a Diagnostic Check

Extracted from the real M4 checks (`core/diagnostics.py`). A diagnostic check is a **pure
function** from Optional input data to a `DiagnosticResult` — it never does I/O, never
raises, and never contains prose. Reference implementations: `check_battery_wear`
(threshold reuse from `battery_analysis`), `check_thermal` (plausibility filtering),
`check_storage_health` (privileged input, skip codes).

Checklist:

1. **Decide the input data.** A check consumes core models the providers already return
   (`list[TemperatureReading]`, `list[SmartReport]`, …). If the data needs a new source,
   write the provider first (`docs/guides/adding-a-provider.md`) — the check itself must
   stay pure.
2. **Write the check** in `core/diagnostics.py`:
   - Signature: `def check_<thing>(data: <T> | None) -> DiagnosticResult`.
   - `None` input = the source couldn't answer → `SKIPPED` with a `skip_code` from the
     established set (`unavailable`, `no-data`, `declined`, `not-requested`). Empty input
     usually means "nothing to assess on this machine" → `SKIPPED("no-data")`, not a
     failure (a desktop has no battery; that's data).
   - Verdict thresholds are named module constants with a comment saying where they come
     from. If another core module already owns the domain rubric (battery_analysis),
     reuse it — never fork thresholds.
   - Set `confidence` honestly: HIGH only when the signal is direct and complete; drop to
     MEDIUM when coverage varies by hardware (thermal) or the source has freshness caveats
     (firmware metadata).
   - Evidence goes in `metrics` as `(machine_key, value_string)` pairs — **no English**.
     Reuse existing keys where they fit; unit suffixes `_pct` / `_c` get formatting for
     free in the UI.
3. **Wire it into `run()`**: gather the input with the per-source try/except pattern
   (a failed source becomes `None`, never an exception to the caller), and add the check
   to the `results` tuple. If the input needs privilege, it must be gated behind an
   explicit flag like `include_storage_health` — `run()` must never prompt unless the
   caller's UI action is visually privilege-marked (ADR-0004).
4. **Add the prose** in `ui/pages/diagnostics/view_model.py`: `CHECK_TITLES` entry, any
   new `METRIC_LABELS` keys, and (if you invented a new skip code) `SKIP_TEXT`. This is
   the ONLY place check text is written; reports reuse it.
5. **Tests** (`tests/unit/test_diagnostics.py`): every verdict boundary, the None/empty
   inputs, and — if the check has a hardware quirk — a case built from the real fixture
   values (the thermal check's test uses the E16's measured 2 °C artifact).
6. **Score impact is automatic** (transparent average over measured checks) — do NOT add
   per-check weights without an ADR; explainability is a constitution invariant.
7. **Docs**: if the check consumed a new provider, its section in
   `docs/modules/providers.md`; the milestone status file ticked.
