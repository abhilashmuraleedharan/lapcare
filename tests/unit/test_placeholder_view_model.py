# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference view-model tests: state transitions, no display required."""

from __future__ import annotations

from lapcare.ui.pages.placeholder.view_model import STATES, PlaceholderViewModel


def test_initial_state_is_loading() -> None:
    assert PlaceholderViewModel().props.state == "loading"


def test_transitions() -> None:
    vm = PlaceholderViewModel()
    vm.show_ready()
    assert vm.props.state == "ready"
    vm.show_unavailable("tool missing", "install it")
    assert vm.props.state == "unavailable"
    assert vm.props.unavailable_reason == "tool missing"
    assert vm.props.unavailable_remedy == "install it"
    vm.show_error("boom")
    assert vm.props.state == "error"
    assert vm.props.error_detail == "boom"
    vm.show_loading()
    assert vm.props.state == "loading"


def test_notify_signal_fires_on_state_change() -> None:
    vm = PlaceholderViewModel()
    seen: list[str] = []
    vm.connect("notify::state", lambda o, _p: seen.append(o.props.state))
    vm.show_ready()
    vm.demo_error()
    assert seen == ["ready", "error"]


def test_advance_cycles_all_states() -> None:
    vm = PlaceholderViewModel()
    visited = [vm.advance() for _ in STATES]
    assert visited == ["ready", "unavailable", "error", "loading"]
    # unavailable/error demo content is well-formed (reason AND remedy)
    assert vm.props.unavailable_reason and vm.props.unavailable_remedy
    assert vm.props.error_detail
