# The privileged helper (ADR-0006): source is an importable/lintable module
# name; the installed name is the canonical path the polkit policy's
# exec.path annotation and the client both reference.
install_data('lapcare_helper.py',
  rename: 'lapcare-helper',
  install_dir: get_option('libexecdir') / 'lapcare',
  install_mode: 'rwxr-xr-x',
)
