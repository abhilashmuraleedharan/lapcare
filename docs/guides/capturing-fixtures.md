# Guide: Capturing Hardware Fixtures

Fixtures are how Lapcare learns what real hardware does — every capture makes the app
more correct on machines the maintainers don't own. Schema and review checklist:
`docs/testing.md`. Implementation: `src/lapcare/capture.py`.

## Capturing (any user)

```sh
lapcare --capture-fixtures            # writes ./lapcare-fixtures/
lapcare --capture-fixtures /tmp/cap   # explicit directory
```

From a source checkout: `PYTHONPATH=src python3 -m lapcare --capture-fixtures`.

The capture is **redacted by default**: DMI serial/UUID/asset-tag files are never read,
and the hostname is replaced with `redacted-host`. The generated `README.md` records the
machine slug, date, kernel, and redaction status. Attach the whole directory (zipped) to a
[hardware report issue](../../.github/ISSUE_TEMPLATE/hardware_report.yml).

`--include-identifiers` exists for local debugging only — its output says "IDENTIFIERS
INCLUDED" in the README and will not be merged.

## Adding a capture to the corpus (contributor/maintainer)

1. Drop the `<source>/<machine>/` directories into `tests/fixtures/`.
2. Run the maintainer review checklist from `docs/testing.md` (no identifiers, README
   present, quirks documented, at least one test reads the fixture).
3. Add/extend a test in `tests/providers/` asserting real values from the capture — a
   fixture no test reads is corpus rot.
4. If the capture revealed a quirk (field missing, odd format), document it in the
   provider's module docstring AND `docs/modules/providers.md`.

## Extending the capture tool

When a new provider lands, add its file manifest or command to `capture.py` (mirroring
exactly what the provider documents reading) and extend `tests/unit/test_capture.py` —
including proving any new identifier-bearing file is redacted by default.
