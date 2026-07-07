# Guide: Adding a UI Page

Extracted from the real M1 pages. Reference implementations: data page →
`src/lapcare/ui/pages/dashboard/`; page with dynamic lists →
`src/lapcare/ui/pages/hardware/`; the pattern demo → `ui/pages/placeholder/`.

A page is a directory under `src/lapcare/ui/pages/<name>/` with three files:

1. **`view_model.py`** — subclass `PageViewModel` (`ui/pages/base_view_model.py`), which
   provides the four-state contract (`state` property, `show_*`, and `handle_error` — the
   single place core errors become translated text with remedies).
   - Constructor: `(scheduler, <ports…>)` — ports only, never concrete providers.
   - `load()`: `show_loading()` then `self._scheduler.submit(self._gather(), self._apply,
     self.handle_error)`.
   - `async _gather()`: awaits the ports, returns a tuple of models.
   - `_apply(data)`: finalize DISPLAY STRINGS here (placeholders "—", humanized units),
     set properties, `show_ready()`. Views only copy strings into rows.
2. **`page.blp`** — Blueprint template `$Lapcare<Name>Page: Adw.Bin` containing a
   `Gtk.Stack stack` with exactly four `StackPage`s named `loading` / `ready` /
   `unavailable` / `error`. Ready content is an `Adw.PreferencesPage` with property-styled
   `Adw.ActionRow`s. `unavailable`/`error` are named `Adw.StatusPage`s. All user-visible
   strings `_("…")`. Register the compiled `.ui` in `src/lapcare.gresource.xml` and the
   `.blp` in the blueprints target in `src/meson.build`.
3. **`view.py`** — `@Gtk.Template` class; children for stack, status pages, rows. In
   `__init__`: store the vm, `connect("notify::state", …)`, call `vm.load()`. The state
   handler copies vm strings into widgets and sets `stack.set_visible_child_name(state)`.
   No hardware logic; no `if` about data meaning.

Then:

4. **Wire it** in `app.py` `do_activate`: construct the vm with ports + scheduler, append
   `(page_id, _("Title"), Page(vm))` to `pages`. Sidebar and navigation are automatic
   (`MainWindow._register_page`); re-selection re-parenting is already guarded.
5. **Meson**: add the three python files to `py.install_sources` in `src/meson.build`.
6. **Tests** (`tests/unit/test_<name>_view_model.py`): drive the vm display-free with
   `ImmediateScheduler` (see `test_dashboard_view_model.py`) over real fixtures; cover
   ready, unavailable, and error states.
7. **Smoke**: nothing to do — `LAPCARE_SMOKE=1` visits every registered page; add a
   `log.debug("<name> ready …")` in `_apply` and assert it in `tests/smoke/test_launch.py`.
8. **DoD**: `./check` both LTS + smoke green; status file ticked; strings translatable.
