# Python sources are listed explicitly (not globbed/install_subdir) so the
# installed payload is deterministic and adding a file is a conscious act.
py.install_sources(
  [
    'lapcare/__init__.py',
    'lapcare/__main__.py',
    'lapcare/app.py',
  ],
  subdir: 'lapcare',
)
py.install_sources(
  [
    'lapcare/core/__init__.py',
    'lapcare/core/ports.py',
  ],
  subdir: 'lapcare/core',
)
py.install_sources(['lapcare/providers/__init__.py'], subdir: 'lapcare/providers')
py.install_sources(
  [
    'lapcare/platform/__init__.py',
    'lapcare/platform/log.py',
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

launcher_conf = configuration_data()
launcher_conf.set('PYTHON', py.full_path())
launcher_conf.set('pythondir', py.get_install_dir())

configure_file(
  input: 'lapcare.in',
  output: 'lapcare',
  configuration: launcher_conf,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)
