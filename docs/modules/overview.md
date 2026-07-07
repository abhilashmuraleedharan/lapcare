# Module Docs — Overview

Per-module purpose and public surface. Grows as modules grow; provider quirks live in
[providers.md](providers.md).

## core

Pure Python, no I/O. `models.py` (frozen dataclasses + `Availability`), `errors.py` (the
exception hierarchy providers translate into), `ports.py` (ALL Protocol interfaces:
providers + `Scheduler`; later `HistoryStore`/`ReportWriter`). Analysis/diagnostics/report
modules arrive M2+.

## platform

OS plumbing implementing core ports. `scheduler.py` (ADR-0007: native gi.events vs
thread-loop fallback — the only sanctioned thread), `subprocess.py` (the audited runner +
`ALLOWED_TOOLS` whitelist), `files.py` (bounded sysfs/proc reads), `log.py` (stderr →
journal). GSettings wrapper and HistoryStore arrive with their consumers.

## ui

`window.py` (NavigationSplitView shell; pages injected by the composition root;
LAPCARE_SMOKE visits all pages), `pages/base_view_model.py` (four-state contract +
error→text mapping), one directory per page (`dashboard/`, `hardware/`, `placeholder/`).
Recipe: `docs/guides/adding-a-page.md`.

## app.py (composition root)

The only module that constructs concrete providers/schedulers and wires them into pages.
Also hosts the CLI (`--version`, `--verbose`, `--capture-fixtures`).

## capture.py

Headless fixture capture with capture-time redaction; guide:
`docs/guides/capturing-fixtures.md`.
