# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider layer: one adapter module per external data source.

Each provider implements ports from lapcare.core.ports, owns ALL knowledge of
its source's quirks (paths, schemas, formats), and reports availability().
First providers arrive in milestone M1. May import core and platform; never ui.
"""
