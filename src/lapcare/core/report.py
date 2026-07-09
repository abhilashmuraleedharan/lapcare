# SPDX-License-Identifier: GPL-3.0-or-later
"""Machine-readable diagnostic report (JSON) — the redacted-by-default export.

Pure: callers supply every input including the timestamp. The JSON document
uses raw check ids, metric keys and enum values (never translated prose) so
it is stable for tooling and bug reports across locales.

Redaction (security-design.md): identifiers never enter this document — the
identity section carries model/machine-type/BIOS only, and there is no
serial key at all. The opt-in unredacted export is deferred until the
ADR-0006 ``dmi-full`` verb exists: unprivileged Lapcare cannot read the DMI
serial anyway, so an "include identifiers" toggle today would be a lie.
Human-readable renderings (Markdown/HTML) are presentation and live in the
UI layer, built from the same translated display data the page shows.
"""

from __future__ import annotations

import json

from lapcare.core.models import DiagnosticsReport, OsInfo, SystemIdentity

SCHEMA_VERSION = 1


def to_json(
    *,
    generated: str,
    app_version: str,
    identity: SystemIdentity | None,
    os_info: OsInfo | None,
    diagnostics: DiagnosticsReport,
) -> str:
    system: dict[str, str | None] = {}
    if identity is not None:
        system["model"] = identity.product_family
        system["machine_type"] = identity.product_name
        system["vendor"] = identity.vendor
        system["bios_version"] = identity.bios_version
        # No serial key, ever — redaction by construction, not by filtering.
    if os_info is not None:
        system["os"] = os_info.distro_name
        system["kernel"] = os_info.kernel

    doc = {
        "lapcare_report": SCHEMA_VERSION,
        "generated": generated,
        "app_version": app_version,
        "redacted": True,
        "system": system,
        "diagnostics": {
            "score": diagnostics.score,
            "measured": diagnostics.measured,
            "total": diagnostics.total,
            "checks": [
                {
                    "id": result.check_id,
                    "status": result.status.value,
                    "confidence": result.confidence.value,
                    "skip_code": result.skip_code or None,
                    "metrics": dict(result.metrics),
                }
                for result in diagnostics.results
            ],
        },
    }
    return json.dumps(doc, indent=2) + "\n"
