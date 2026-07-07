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
    'lapcare/core/errors.py',
    'lapcare/core/models.py',
    'lapcare/core/ports.py',
  ],
  subdir: 'lapcare/core',
)
py.install_sources(
  [
    'lapcare/providers/__init__.py',
    'lapcare/providers/dmi.py',
    'lapcare/providers/os_info.py',
    'lapcare/providers/pci_usb.py',
    'lapcare/providers/thinkpad_acpi.py',
  ],
  subdir: 'lapcare/providers',
)
py.install_sources(
  [
    'lapcare/platform/__init__.py',
    'lapcare/platform/files.py',
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
py.install_sources(['lapcare/ui/pages/__init__.py'], subdir: 'lapcare/ui/pages')
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
    'lapcare/ui/pages/placeholder/page.blp',
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
