# SPDX-License-Identifier: GPL-3.0-or-later
"""Report export: JSON schema, MD/HTML rendering, redaction guarantees, and
the view-model export flow through a fake writer."""

from __future__ import annotations

import json

from lapcare.core import report as core_report
from lapcare.core.models import (
    CheckStatus,
    Confidence,
    DiagnosticResult,
    DiagnosticsReport,
    OsInfo,
    SystemIdentity,
)
from lapcare.providers.dmi import DmiSysfs
from lapcare.providers.os_info import OsInfoProc
from lapcare.ui.pages.diagnostics import report_render
from lapcare.ui.pages.diagnostics.view_model import result_cards, score_texts

from ..providers.conftest import fixture_root
from .test_dashboard_view_model import ImmediateScheduler
from .test_diagnostics_view_model import _vm as make_diagnostics_vm

REPORT = DiagnosticsReport(
    results=(
        DiagnosticResult(
            check_id="battery-wear",
            status=CheckStatus.OK,
            confidence=Confidence.HIGH,
            metrics=(("wear_pct", "5.0"),),
        ),
        DiagnosticResult(
            check_id="storage-health",
            status=CheckStatus.SKIPPED,
            confidence=Confidence.LOW,
            skip_code="declined",
        ),
    ),
    score=100,
    measured=1,
    total=2,
)
IDENTITY = SystemIdentity(
    vendor="LENOVO",
    product_family="ThinkPad E16 Gen 2",
    product_name="21MBCTO1WW",
    bios_version="R2JET48W(1.25 )",
    serial="SECRET-SERIAL-42",  # must never surface anywhere
)
OS = OsInfo(distro_name="Ubuntu 24.04.2 LTS", kernel="6.8.0-124-generic")


def test_json_schema_and_redaction() -> None:
    text = core_report.to_json(
        generated="2026-07-10 00:00 UTC",
        app_version="0.5.0",
        identity=IDENTITY,
        os_info=OS,
        diagnostics=REPORT,
    )
    doc = json.loads(text)
    assert doc["lapcare_report"] == 1
    assert doc["redacted"] is True
    assert doc["system"]["model"] == "ThinkPad E16 Gen 2"
    assert doc["diagnostics"]["score"] == 100
    check = doc["diagnostics"]["checks"][0]
    assert check == {
        "id": "battery-wear",
        "status": "ok",
        "confidence": "high",
        "skip_code": None,
        "metrics": {"wear_pct": "5.0"},
    }
    assert doc["diagnostics"]["checks"][1]["skip_code"] == "declined"
    # Redaction by construction: no serial key, no serial value.
    assert "serial" not in json.dumps(doc["system"]).lower()
    assert "SECRET-SERIAL-42" not in text


def render_args() -> dict:  # type: ignore[type-arg]
    headline, coverage = score_texts(REPORT)
    return {
        "generated": "2026-07-10 00:00 UTC",
        "app_version": "0.5.0",
        "system_rows": [("Model", "ThinkPad E16 Gen 2")],
        "score_text": headline,
        "coverage_text": coverage,
        "cards": result_cards(REPORT),
    }


def test_markdown_render() -> None:
    text = report_render.render_markdown(**render_args())
    assert "# Lapcare Diagnostic Report" in text
    assert "- Model: ThinkPad E16 Gen 2" in text
    assert "**100 / 100**" in text
    assert "### Battery wear — OK" in text
    assert "- Worst battery wear: 5.0%" in text
    assert "### Storage health — Not measured" in text
    assert "declined" in text
    assert "excluded" in text  # the redaction notice


def test_html_render_escapes() -> None:
    args = render_args()
    args["system_rows"] = [("Model", "<script>alert(1)</script>")]
    text = report_render.render_html(**args)
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text
    assert text.startswith("<!DOCTYPE html>")
    assert "Battery wear" in text


class FakeWriter:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.written: dict[str, str] = {}

    def write(self, path: str, content: str) -> None:
        if self.error is not None:
            raise self.error
        self.written[path] = content


def _export_vm(writer: FakeWriter):  # type: ignore[no-untyped-def]
    vm = make_diagnostics_vm()
    vm._writer = writer
    vm._identity = DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2"))
    vm._os_info = OsInfoProc(root=fixture_root("os_info", "synthetic-full"))
    vm._scheduler = ImmediateScheduler()
    vm.load()
    return vm


def test_export_flow_all_three_formats() -> None:
    writer = FakeWriter()
    vm = _export_vm(writer)
    assert not vm.can_export  # nothing to export before a run
    vm.run()
    assert vm.can_export
    for path in ("/tmp/r.md", "/tmp/r.html", "/tmp/r.json"):
        vm.export(path)
    assert vm.props.toast_text == "Report exported."
    assert "# Lapcare Diagnostic Report" in writer.written["/tmp/r.md"]
    assert writer.written["/tmp/r.html"].startswith("<!DOCTYPE html>")
    doc = json.loads(writer.written["/tmp/r.json"])
    assert doc["system"]["model"] == "ThinkPad E16 Gen 2"
    assert doc["diagnostics"]["score"] == 100
    # Redaction across every format: no serial row/key ever (the redaction
    # NOTICE legitimately mentions the words "serial numbers").
    for content in writer.written.values():
        assert "Serial:" not in content
        assert '"serial"' not in content


def test_export_write_failure_is_toast_not_error_page() -> None:
    writer = FakeWriter(error=OSError("disk full"))
    vm = _export_vm(writer)
    vm.run()
    vm.export("/tmp/r.md")
    assert vm.props.state == "ready"
    assert "Could not export" in vm.props.toast_text
    assert vm.props.busy_text == ""
