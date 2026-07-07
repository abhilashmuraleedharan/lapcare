# SPDX-License-Identifier: GPL-3.0-or-later
"""Ports: the Protocol interfaces implemented by providers and platform.

This module is the architectural boundary described in ARCHITECTURE.md — the
UI and core depend on these interfaces; adapters implement them; only the
composition root (app.py) sees concrete classes.

Grows with milestone M1 (first providers: dmi, os_info, pci_usb,
thinkpad_acpi) and M2 (HistoryStore). Stdlib imports only.
"""
