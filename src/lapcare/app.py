# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point and composition root.

The only module that constructs concrete implementations and wires them
together (see ARCHITECTURE.md). Provider wiring begins in M1.

GTK/libadwaita are imported lazily inside _build_application() so that
--version/--help and unit tests work without a display or GTK stack.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from lapcare import APP_ID, __version__
from lapcare.platform import log as platform_log

log = logging.getLogger(__name__)


def _load_resources() -> None:
    """Register the gresource bundle (compiled Blueprint UI definitions).

    Must run before any ui module is imported: Gtk.Template decorators read
    resources at class-definition time. The path comes from LAPCARE_RESOURCE,
    set by the installed launcher (pkgdatadir) or by ./run (build dir).
    """
    from gi.repository import Gio

    path = os.environ.get("LAPCARE_RESOURCE")
    if not path or not os.path.exists(path):
        raise RuntimeError(
            "UI resources not found (LAPCARE_RESOURCE unset or missing). "
            "Run via ./run or the installed 'lapcare' command."
        )
    Gio.resources_register(Gio.Resource.load(path))
    log.debug("resources registered from %s", path)


def _build_application(scheduler):  # -> Adw.Application (typed loosely: gi is untyped)
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gettext import gettext as _

    from gi.repository import Adw, Gio, GLib

    _load_resources()
    # Providers and pages are imported and WIRED here and only here — the
    # composition root is the one module that sees concrete classes.
    from lapcare.platform.history import SqliteHistoryStore
    from lapcare.platform.report import TextReportWriter
    from lapcare.providers.battery_sysfs import BatterySysfs
    from lapcare.providers.disk_usage import DiskUsageStatvfs
    from lapcare.providers.dmi import DmiSysfs
    from lapcare.providers.fwupd import FwupdGir
    from lapcare.providers.hwmon import HwmonSysfs
    from lapcare.providers.os_info import OsInfoProc
    from lapcare.providers.pci_usb import PciUsbTools
    from lapcare.providers.storage_smart import StorageSmartPkexec
    from lapcare.providers.thinkpad_acpi import ThinkpadAcpiSysfs
    from lapcare.providers.upower import UPowerDbus
    from lapcare.ui.pages.battery.view import BatteryPage
    from lapcare.ui.pages.battery.view_model import BatteryViewModel
    from lapcare.ui.pages.dashboard.view import DashboardPage
    from lapcare.ui.pages.dashboard.view_model import DashboardViewModel
    from lapcare.ui.pages.diagnostics.view import DiagnosticsPage
    from lapcare.ui.pages.diagnostics.view_model import DiagnosticsViewModel
    from lapcare.ui.pages.firmware.view import FirmwarePage
    from lapcare.ui.pages.firmware.view_model import FirmwareViewModel
    from lapcare.ui.pages.hardware.view import HardwarePage
    from lapcare.ui.pages.hardware.view_model import HardwareViewModel
    from lapcare.ui.pages.placeholder.view import PlaceholderPage
    from lapcare.ui.pages.placeholder.view_model import PlaceholderViewModel
    from lapcare.ui.pages.storage.view import StoragePage
    from lapcare.ui.pages.storage.view_model import StorageViewModel
    from lapcare.ui.window import MainWindow

    class LapcareApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id=APP_ID,
                flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            )
            # Keyboard access (ROADMAP M5): standard GNOME app shortcuts.
            quit_action = Gio.SimpleAction.new("quit", None)
            quit_action.connect("activate", lambda *_a: self.quit())
            self.add_action(quit_action)
            self.set_accels_for_action("app.quit", ["<Control>q"])
            self.set_accels_for_action("window.close", ["<Control>w"])

        def do_activate(self) -> None:
            window = self.props.active_window
            if window is None:
                dmi = DmiSysfs()
                os_info = OsInfoProc()
                thinkpad = ThinkpadAcpiSysfs(identity=dmi)
                inventory = PciUsbTools()
                battery_wear = BatterySysfs()
                firmware = FwupdGir()
                storage = StorageSmartPkexec()
                thermal = HwmonSysfs()
                disk = DiskUsageStatvfs()

                dashboard_vm = DashboardViewModel(
                    scheduler,
                    identity=dmi,
                    os_info=os_info,
                    thinkpad=thinkpad,
                    battery_wear=battery_wear,
                    firmware=firmware,
                    thermal=thermal,
                    disk=disk,
                )
                hardware_vm = HardwareViewModel(
                    scheduler, identity=dmi, os_info=os_info, inventory=inventory
                )
                battery_vm = BatteryViewModel(
                    scheduler,
                    wear=battery_wear,
                    status=UPowerDbus(),
                    history=SqliteHistoryStore(),
                )
                firmware_vm = FirmwareViewModel(scheduler, firmware=firmware)
                storage_vm = StorageViewModel(scheduler, storage=storage)
                diagnostics_vm = DiagnosticsViewModel(
                    scheduler,
                    battery_wear=battery_wear,
                    storage=storage,
                    firmware=firmware,
                    thermal=thermal,
                    disk=disk,
                    identity=dmi,
                    os_info=os_info,
                    writer=TextReportWriter(),
                )
                pages = [
                    ("dashboard", _("Dashboard"), DashboardPage(dashboard_vm)),
                    ("battery", _("Battery"), BatteryPage(battery_vm)),
                    ("hardware", _("Hardware"), HardwarePage(hardware_vm)),
                    ("firmware", _("Firmware"), FirmwarePage(firmware_vm)),
                    ("storage", _("Storage"), StoragePage(storage_vm)),
                    ("diagnostics", _("Diagnostics"), DiagnosticsPage(diagnostics_vm)),
                    ("reference", _("Reference"), PlaceholderPage(PlaceholderViewModel())),
                ]
                window = MainWindow(application=self, pages=pages)
            window.present()
            from lapcare import launch_elapsed_s

            log.info("window presented elapsed=%.3fs", launch_elapsed_s() or -1.0)

            # Dev/CI hook (used by the smoke test): auto-quit after N ms.
            auto_quit_ms = os.environ.get("LAPCARE_AUTO_QUIT_MS")
            if auto_quit_ms is not None:
                GLib.timeout_add(int(auto_quit_ms), self.quit)

    return LapcareApplication()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lapcare",
        description="Battery health, firmware updates and diagnostics for ThinkPads.",
    )
    parser.add_argument("--version", action="version", version=f"lapcare {__version__}")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    parser.add_argument(
        "--capture-fixtures",
        nargs="?",
        const="lapcare-fixtures",
        metavar="DIR",
        help="capture this machine's data as test fixtures (headless) and exit",
    )
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
        help="with --capture-fixtures: keep serials/UUIDs/hostname (LOCAL DEBUGGING ONLY)",
    )
    args = parser.parse_args(argv)

    platform_log.configure(verbose=args.verbose)
    log.info("starting version=%s", __version__)

    if args.capture_fixtures:
        from pathlib import Path

        from lapcare.capture import run_capture

        return run_capture(
            Path(args.capture_fixtures), include_identifiers=args.include_identifiers
        )

    # Scheduler must exist before the GLib main loop starts (ADR-0007); it is
    # handed to view-models when pages arrive (M1).
    from lapcare.platform.scheduler import create_scheduler

    scheduler = create_scheduler()
    scheduler.start()
    try:
        app = _build_application(scheduler)
        return int(app.run([sys.argv[0]]))
    finally:
        scheduler.stop()
