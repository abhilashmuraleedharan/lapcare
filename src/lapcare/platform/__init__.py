# SPDX-License-Identifier: GPL-3.0-or-later
"""Platform layer: OS plumbing behind core ports.

D-Bus connections, the single audited subprocess runner, the async scheduler
(ADR-0007), HistoryStore/ReportWriter implementations, GSettings, logging and
XDG paths. May import stdlib, GLib, and core ports; never providers or ui.
"""
