# SPDX-License-Identifier: GPL-3.0-or-later
"""Core domain layer: pure Python, no I/O, stdlib imports only.

Models, analysis, diagnostics, and report rendering live here, together with
the port interfaces (ports.py) that providers and platform implement. Enforced
by import-linter: this package must never import gi, providers, platform or ui.
"""
