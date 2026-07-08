"""fwupd mock template (local — python-dbusmock ships none upstream; see ADR-0009).

Minimal subset of org.freedesktop.fwupd needed to test providers/fwupd.py's
read-only surface and error-translation paths: GetDevices, GetUpgrades,
GetReleases, GetRemotes, GetDeviceByGuid-equivalent lookup, plus convenience
methods (AddDevice/AddUpgrade/AddRemote) mirroring python-dbusmock's own
upower.py template style. Real network-touching operations
(refresh_remote()/install_release()'s in-process download — see ADR-0009)
are NOT exercised against a live remote here; those paths are unit-tested by
constructing GLib.Error instances directly (tests/providers/test_fwupd.py).
"""

import dbus

BUS_NAME = "org.freedesktop.fwupd"
MAIN_OBJ = "/"
MAIN_IFACE = "org.freedesktop.fwupd"
SYSTEM_BUS = True


def load(mock, parameters):
    mock._devices = {}
    mock._upgrades = {}
    mock._remotes = []

    mock.AddMethods(
        MAIN_IFACE,
        [
            ("GetDevices", "", "aa{sv}", "ret = list(self._devices.values())"),
            (
                "GetDeviceById",
                "s",
                "a{sv}",
                "ret = self._devices[args[0]]",
            ),
            ("GetUpgrades", "s", "aa{sv}", "ret = self._upgrades.get(args[0], [])"),
            ("GetReleases", "s", "aa{sv}", "ret = self._upgrades.get(args[0], [])"),
            ("GetRemotes", "", "aa{sv}", "ret = self._remotes"),
        ],
    )

    props = dbus.Dictionary(
        {
            "DaemonVersion": parameters.get("DaemonVersion", "1.9.0"),
            "Percentage": dbus.UInt32(0),
            "Status": dbus.UInt32(0),
            "BatteryLevel": dbus.UInt32(parameters.get("BatteryLevel", 101)),
            "BatteryThreshold": dbus.UInt32(parameters.get("BatteryThreshold", 101)),
        },
        signature="sv",
    )
    mock.AddProperties(MAIN_IFACE, props)


@dbus.service.method(MAIN_IFACE, in_signature="sa{sv}", out_signature="")
def AddDevice(self, device_id, properties):
    """Add a device dict (keys/types match Fwupd.Device properties, e.g.
    DeviceId, Name, Version, VersionLowest, Vendor, Plugin, Flags (uint64),
    UpdateState (uint32), UpdateError)."""
    props = dbus.Dictionary(properties, signature="sv")
    props["DeviceId"] = dbus.String(device_id)
    self._devices[device_id] = props
    self.EmitSignal(MAIN_IFACE, "DeviceAdded", "a{sv}", [props])


@dbus.service.method(MAIN_IFACE, in_signature="sa{sv}", out_signature="")
def AddUpgrade(self, device_id, properties):
    """Add a release dict (keys match Fwupd.Release properties, e.g.
    Version, Name, Summary, Description, Size (uint64), Urgency (uint32),
    Locations (array of string URIs))."""
    props = dbus.Dictionary(properties, signature="sv")
    self._upgrades.setdefault(device_id, []).append(props)


@dbus.service.method(MAIN_IFACE, in_signature="sa{sv}", out_signature="")
def AddRemote(self, remote_id, properties):
    props = dbus.Dictionary(properties, signature="sv")
    props["RemoteId"] = dbus.String(remote_id)
    self._remotes.append(props)
