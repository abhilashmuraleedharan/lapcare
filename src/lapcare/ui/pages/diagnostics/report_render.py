# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-readable report renderings (Markdown, HTML).

Presentation-layer by design: both formats are built from the same
translated display data the Diagnostics page shows (CheckCard rows), so the
exported document matches the screen in the user's language. The
machine-readable JSON export lives in core/report.py. Both are redacted by
default — these renderers only ever see data with no identifiers in it.
"""

from __future__ import annotations

import html
from gettext import gettext as _

from lapcare.ui.pages.diagnostics.view_model import CheckCard


def render_markdown(
    *,
    generated: str,
    app_version: str,
    system_rows: list[tuple[str, str]],
    score_text: str,
    coverage_text: str,
    cards: list[CheckCard],
) -> str:
    lines = [
        _("# Lapcare Diagnostic Report"),
        "",
        _("- Generated: %s") % generated,
        _("- Lapcare version: %s") % app_version,
        _("- Identifiers (serial numbers etc.) are excluded from this report."),
        "",
    ]
    if system_rows:
        lines += [_("## System"), ""]
        lines += [f"- {label}: {value}" for label, value in system_rows]
        lines.append("")
    lines += [_("## Health Score"), "", f"**{score_text}** — {coverage_text}", ""]
    lines += [_("## Checks"), ""]
    for card in cards:
        lines.append(f"### {card.title} — {card.status_text}")
        lines.append("")
        lines.append(card.subtitle)
        if card.evidence:
            lines.append("")
            lines += [f"- {label}: {value}" for label, value in card.evidence]
        lines.append("")
    return "\n".join(lines)


def render_html(
    *,
    generated: str,
    app_version: str,
    system_rows: list[tuple[str, str]],
    score_text: str,
    coverage_text: str,
    cards: list[CheckCard],
) -> str:
    e = html.escape

    def rows_table(rows: list[tuple[str, str]]) -> str:
        cells = "".join(f"<tr><th>{e(label)}</th><td>{e(value)}</td></tr>" for label, value in rows)
        return f"<table>{cells}</table>"

    css_status = {"success": "#1a7f37", "warning": "#9a6700", "error": "#cf222e"}
    parts = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8">',
        f"<title>{e(_('Lapcare Diagnostic Report'))}</title>",
        "<style>body{font-family:sans-serif;max-width:48rem;margin:2rem auto;"
        "padding:0 1rem}table{border-collapse:collapse}th,td{text-align:left;"
        "padding:.2rem .8rem .2rem 0}th{font-weight:600}</style>",
        "</head><body>",
        f"<h1>{e(_('Lapcare Diagnostic Report'))}</h1>",
        "<p>"
        + e(_("Generated: %s") % generated)
        + "<br>"
        + e(_("Lapcare version: %s") % app_version)
        + "<br>"
        + e(_("Identifiers (serial numbers etc.) are excluded from this report."))
        + "</p>",
    ]
    if system_rows:
        parts.append(f"<h2>{e(_('System'))}</h2>")
        parts.append(rows_table(system_rows))
    parts.append(f"<h2>{e(_('Health Score'))}</h2>")
    parts.append(f"<p><strong>{e(score_text)}</strong> — {e(coverage_text)}</p>")
    parts.append(f"<h2>{e(_('Checks'))}</h2>")
    for card in cards:
        color = css_status.get(card.status_css, "#57606a")
        parts.append(
            f'<h3>{e(card.title)} — <span style="color:{color}">{e(card.status_text)}</span></h3>'
        )
        parts.append(f"<p>{e(card.subtitle)}</p>")
        if card.evidence:
            parts.append(rows_table(card.evidence))
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"
