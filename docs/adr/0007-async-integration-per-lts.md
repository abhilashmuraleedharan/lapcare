# ADR-0007: Async integration per Ubuntu LTS

- **Status:** Accepted
- **Date:** 2026-07-07
- **Deciders:** Lead Architect, from M0 stack-validation spike (Commit 9)

## Context

Lapcare's concurrency model is `async def` provider I/O on top of the GTK main loop.
PyGObject's native asyncio integration (`gi.events.GLibEventLoopPolicy`) landed in PyGObject
3.50. The M0 spike (`tools/stack_probe.py`, run in clean `ubuntu:24.04` and `ubuntu:26.04`
containers on 2026-07-07) measured the supported targets:

| Component | Ubuntu 24.04 | Ubuntu 26.04 | Verdict |
|---|---|---|---|
| Python | 3.12.3 | 3.14.4 | ≥ 3.12 floor holds |
| PyGObject | 3.48.2 | 3.56.2 | **24.04 lacks `gi.events`** |
| `gi.events` | absent | available | the fork this ADR resolves |
| GLib | 2.80.0 | 2.88.0 | fine |
| GTK | 4.14.5 | 4.22.4 | fine |
| libadwaita | 1.5.0 | 1.9.0 | ≥ 1.4 holds (NavigationSplitView available) |
| blueprint-compiler | 0.12.0 | 0.19.0 | fine |
| python3-dbusmock | 0.31.1 | 0.38.1 | fine |
| Meson | 1.3.2 | 1.10.1 | ≥ 1.3 floor holds |

## Decision

`lapcare/platform/scheduler.py` exposes **one scheduler interface** with two implementations,
selected at startup by probing `import gi.events`:

1. **Native (PyGObject ≥ 3.50, i.e. Ubuntu 26.04+):** install
   `gi.events.GLibEventLoopPolicy`; coroutines run on the GLib main loop directly.
2. **Thread-loop fallback (PyGObject < 3.50, i.e. Ubuntu 24.04):** one dedicated background
   thread running a plain asyncio event loop; coroutines are submitted with
   `asyncio.run_coroutine_threadsafe`, and completion callbacks are marshaled back to the GTK
   main thread via `GLib.idle_add`.

Provider and view-model code is **identical under both**: providers are `async def`;
view-models hand coroutines to the scheduler and receive callbacks on the main thread. The
background loop thread is the *only* sanctioned thread in the process (constitution
invariant: no ad-hoc threads); it is owned, started, and stopped by the platform layer.

This refines plan v1.1's "shared thread-pool executor" wording: a single background asyncio
loop is strictly better than a thread pool here because provider code stays uniformly async —
no dual sync/async code paths, no per-call thread hops — while keeping the same
one-sanctioned-thread posture. `tools/stack_probe.py` is kept permanently as an environment
diagnostic.

## Consequences

- The 24.04 fallback carries the complexity (thread-safety at exactly one boundary:
  `run_coroutine_threadsafe` in, `GLib.idle_add` out). C11 must test both mechanisms.
- When Ubuntu 24.04 leaves the support matrix, the fallback is deleted and the scheduler
  interface stays — no caller changes.
- CI must exercise both LTS containers (full lane, C14) since the two paths differ at runtime.
- No version pins needed in `meson.build` beyond the Python ≥ 3.12 floor; every other floor
  is comfortably met by both targets.

## Alternatives Considered

- **Require PyGObject ≥ 3.50 everywhere** (pip/backport on 24.04): rejected — overriding a
  distro's PyGObject invites ABI mismatch with system GTK typelibs and breaks the
  "distro-native runtime deps" packaging posture (ADR-0005).
- **Thread-pool executor with synchronous providers on 24.04** (plan v1.1's sketch): rejected
  in refinement — would force providers to be written twice or synchronously, poisoning the
  dominant (native) path for the sake of the fallback.
- **gbulb / manual GLib-asyncio bridging libraries:** rejected — unmaintained or redundant
  with `gi.events` on the path where they'd matter.
- **Drop 24.04 support:** rejected — it is a supported LTS until the project says otherwise,
  and the maintainer's own hardware will run it.
