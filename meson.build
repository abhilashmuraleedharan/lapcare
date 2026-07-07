project('lapcare',
  version: '0.1.0',
  meson_version: '>= 1.3.0',
  license: 'GPL-3.0-or-later',
)

app_id = 'io.github.abhilashmuraleedharan.lapcare'

py_mod = import('python')
py = py_mod.find_installation('python3', required: true)
gnome = import('gnome')

if not py.language_version().version_compare('>= 3.12')
  error('lapcare requires Python >= 3.12, found @0@ (see ADR-0003)'.format(py.language_version()))
endif

subdir('src')
subdir('data')

gnome.post_install(
  glib_compile_schemas: true,
  update_desktop_database: true,
)
