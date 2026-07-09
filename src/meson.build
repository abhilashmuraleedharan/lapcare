# Python sources are listed explicitly (not globbed/install_subdir) so the
# installed payload is deterministic and adding a file is a conscious act.
py.install_sources(
  [
    'lapcare/__init__.py',
    'lapcare/__main__.py',
    'lapcare/app.py',
    'lapcare/capture.py',
  ],
  subdir: 'lapcare',
)
py.install_sources(
  [
    'lapcare/core/__init__.py',
    'lapcare/core/battery_analysis.py',
    'lapcare/core/errors.py',
    'lapcare/core/firmware_policy.py',
    'lapcare/core/models.py',
    'lapcare/core/ports.py',
  ],
  subdir: 'lapcare/core',
)
py.install_sources(
  [
    'lapcare/providers/__init__.py',
    'lapcare/providers/battery_sysfs.py',
    'lapcare/providers/dmi.py',
    'lapcare/providers/fwupd.py',
    'lapcare/providers/os_info.py',
    'lapcare/providers/pci_usb.py',
    'lapcare/providers/storage_smart.py',
    'lapcare/providers/thinkpad_acpi.py',
    'lapcare/providers/upower.py',
  ],
  subdir: 'lapcare/providers',
)
py.install_sources(
  [
    'lapcare/platform/__init__.py',
    'lapcare/platform/dbus.py',
    'lapcare/platform/files.py',
    'lapcare/platform/history.py',
    'lapcare/platform/log.py',
    'lapcare/platform/scheduler.py',
    'lapcare/platform/subprocess.py',
  ],
  subdir: 'lapcare/platform',
)
py.install_sources(
  [
    'lapcare/ui/__init__.py',
    'lapcare/ui/window.py',
  ],
  subdir: 'lapcare/ui',
)
py.install_sources(
  [
    'lapcare/ui/pages/__init__.py',
    'lapcare/ui/pages/base_view_model.py',
  ],
  subdir: 'lapcare/ui/pages',
)
py.install_sources(
  [
    'lapcare/ui/pages/battery/__init__.py',
    'lapcare/ui/pages/battery/view.py',
    'lapcare/ui/pages/battery/view_model.py',
  ],
  subdir: 'lapcare/ui/pages/battery',
)
py.install_sources(
  [
    'lapcare/ui/widgets/__init__.py',
    'lapcare/ui/widgets/wear_chart.py',
  ],
  subdir: 'lapcare/ui/widgets',
)
py.install_sources(
  [
    'lapcare/ui/pages/dashboard/__init__.py',
    'lapcare/ui/pages/dashboard/view.py',
    'lapcare/ui/pages/dashboard/view_model.py',
  ],
  subdir: 'lapcare/ui/pages/dashboard',
)
py.install_sources(
  [
    'lapcare/ui/pages/firmware/__init__.py',
    'lapcare/ui/pages/firmware/view.py',
    'lapcare/ui/pages/firmware/view_model.py',
  ],
  subdir: 'lapcare/ui/pages/firmware',
)
py.install_sources(
  [
    'lapcare/ui/pages/hardware/__init__.py',
    'lapcare/ui/pages/hardware/view.py',
    'lapcare/ui/pages/hardware/view_model.py',
  ],
  subdir: 'lapcare/ui/pages/hardware',
)
py.install_sources(
  [
    'lapcare/ui/pages/storage/__init__.py',
    'lapcare/ui/pages/storage/view.py',
    'lapcare/ui/pages/storage/view_model.py',
  ],
  subdir: 'lapcare/ui/pages/storage',
)
py.install_sources(
  [
    'lapcare/ui/pages/placeholder/__init__.py',
    'lapcare/ui/pages/placeholder/view.py',
    'lapcare/ui/pages/placeholder/view_model.py',
  ],
  subdir: 'lapcare/ui/pages/placeholder',
)

# Blueprint -> GtkBuilder XML -> gresource bundle. Loaded at runtime via the
# LAPCARE_RESOURCE env var (set by the installed launcher and by ./run).
blueprint_compiler = find_program('blueprint-compiler')
blueprints = custom_target('blueprints',
  input: files(
    'lapcare/ui/window.blp',
    'lapcare/ui/pages/battery/page.blp',
    'lapcare/ui/pages/dashboard/page.blp',
    'lapcare/ui/pages/firmware/page.blp',
    'lapcare/ui/pages/hardware/page.blp',
    'lapcare/ui/pages/placeholder/page.blp',
    'lapcare/ui/pages/storage/page.blp',
  ),
  output: '.',
  command: [blueprint_compiler, 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

pkgdatadir = get_option('prefix') / get_option('datadir') / 'lapcare'

gnome.compile_resources('lapcare',
  'lapcare.gresource.xml',
  dependencies: blueprints,
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

# NOTE: the launcher (src/lapcare.in) is generated from the ROOT meson.build,
# not here — its output file 'lapcare' would collide with the 'lapcare/'
# directory tree that blueprint batch-compile mirrors into this build dir.
