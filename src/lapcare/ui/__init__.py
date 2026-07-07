# SPDX-License-Identifier: GPL-3.0-or-later
"""UI layer: GTK4/libadwaita views (Blueprint) and view-models.

Depends on core only (models + ports) plus GTK/Adw. Never imports providers
or platform; port implementations are injected by the composition root.
Every page renders one of: loading / ready / unavailable / error.
"""
