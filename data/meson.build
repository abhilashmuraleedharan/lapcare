install_data(app_id + '.desktop',
  install_dir: get_option('datadir') / 'applications',
)
install_data(app_id + '.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo',
)
install_data(app_id + '.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)
install_data(app_id + '.policy',
  install_dir: get_option('datadir') / 'polkit-1' / 'actions',
)

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('validate-desktop-file', desktop_file_validate,
    args: [files(app_id + '.desktop')],
    suite: 'data',
  )
endif

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('validate-metainfo', appstreamcli,
    args: ['validate', '--no-net', files(app_id + '.metainfo.xml')],
    suite: 'data',
  )
endif

glib_compile_schemas = find_program('glib-compile-schemas', required: false)
if glib_compile_schemas.found()
  test('validate-gschema', glib_compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()],
    suite: 'data',
  )
endif
