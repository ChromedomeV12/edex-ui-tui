# Kitty border experiment

## Baseline

Main retains the reviewed tmux layout. Use this branch in a separate worktree for border experiments. Do not replace the running VM session or change normal terminal configuration.

## Experiment session isolation

Run this branch from a separate checkout of the guest source tree, and launch it from a separate real desktop Kitty window that is not a tmux client. `launch.py` refuses a full launch while `TMUX` is set, and unsetting that variable does not help, because you would then start a tmux server inside a tmux client. Leave `XDG_RUNTIME_DIR` as the desktop environment sets it, because the lock files land there.

`EDEX_TMUX_SOCKET` gives the experiment its own tmux server. A non-empty value governs the launcher, the scoped control commands, and the profiler. When the variable is unset or empty, `launch.py` falls back to `edex-terminal-<uid>`. Always supply the experiment selector when running controls outside its panes; omitting it targets the baseline socket. There is no inference from `TMUX`.

The server passes the selector to the children it launches after that point, new panes and key binding commands included. Shells that were already running in a pre-existing session keep their spawn-time environment; the selector is not applied to them retroactively. Set the variable on the command line in those panes, and in the invoking shell when you run controls from outside the server.

The workspace coordination lock is scoped per socket, so two named servers can coexist. It lands under `XDG_RUNTIME_DIR` (or `/tmp`). The graphics serialization lock stays global per uid, because it guards multipart graphics writes at the terminal, and two tmux servers can share one terminal surface.

Example, with the experiment socket `edex-borders`:

```sh
# From a desktop Kitty window outside tmux, in the guest checkout:
EDEX_TMUX_SOCKET=edex-borders python3 launch.py --detach
tmux -L edex-borders attach -t edex

# Scoped controls, from outside or inside tmux:
EDEX_TMUX_SOCKET=edex-borders python3 launch.py --toggle-keyboard
EDEX_TMUX_SOCKET=edex-borders python3 launch.py --install-switcher

# Profiling reads the same resolution:
EDEX_TMUX_SOCKET=edex-borders python3 profile_panes.py
python3 profile_panes.py   # in a pane the server spawned, which inherited the variable

# Tear down the experiment server; the baseline is untouched:
EDEX_TMUX_SOCKET=edex-borders python3 launch.py --stop
tmux -L edex-borders kill-server
```

### Isolation validation

On 2026-10-24, the full suite passed in the disposable Omarchy VM: 27 Python tests and the Lua grid assertions. The isolation tests use concurrent private servers, including one that predates the launcher.

We launched a separate Kitty session from a private source copy and inspected captures of the main layout, keyboard display, and reattachment. Switching slots 1–2–1 preserved the original shell PID and directory. Keyboard show/hide, profiling, detach/reattach, and scoped stop succeeded. A separate guard server kept its pane PID and state. The baseline server was absent before and after the check; we did not exercise a running baseline installation.

One capture taken two seconds after reattachment showed a blank network column. A separate run captured the column visible after eight seconds. These checks do not establish immediate graphics recovery, flicker behavior, or multiple-client support.


## Standalone prototype

A standalone one-shell prototype of the relative-placement frame is on this branch: `border_probe.py` plus its renderer `border_frame.py`, running on a dedicated named tmux server, so the baseline layout and the normal `launch.py` flow are unchanged. A nonempty, nondefault `EDEX_TMUX_SOCKET` is mandatory: the probe rejects an unset or empty value and the launcher's `edex-terminal-<uid>` fallback socket, so it can never join the baseline server. From a desktop Kitty window outside tmux:

```sh
EDEX_TMUX_SOCKET=edex-borders python3 border_probe.py --cwd "$HOME" --detach
tmux -L edex-borders attach -t edex-border-probe
EDEX_TMUX_SOCKET=edex-borders python3 border_probe.py --stop
```

The session `edex-border-probe` carries its own ownership marker. Its five panes are a native shell, a full-width header running `border_frame.py`, and three empty-command gutters with no processes. The header and bottom band reserve two rows; each side reserves two columns, plus tmux's separator cells. The renderer restores these dimensions after resize or reattachment rather than letting tmux expand the gutters. Per-window options hide native border glyphs only in this probe.

The frame adapts the augmented-ui 1.1.2 `tr-clip` and `bl-clip` outer and inner polygons: 15px top-right and bottom-left clips with square opposite corners. Stroke width (0.18vh), opacity (0.5), and padding (0.74vh) come from eDEX's `main_shell.css`. The legacy library matches eDEX's markup, unlike the pinned fork's incompatible augmented-ui 2.0.0 lock entry. NOTICE.md and UPSTREAM.json record the source, checksum, and BSD-2-Clause license. Chromium provides a development reference only; the prototype uses Pillow and Kitty graphics at runtime.

The prototype's scope is one attached client: the frame is sized from the window geometry, and a second client is not claimed or tested. Shell tabs, the keyboard, and Yazi borders are not integrated with the frame, and the native shell keeps its own cursor, input, and selection. Full-layout integration and a default-configuration cutover are not done.

### Prototype validation

On 2026-10-25, the full suite passed in the disposable Omarchy VM: 30 Python tests and the Lua grid assertions. We inspected actual Kitty captures during launch, resize, shell zoom/unzoom, reattachment, and renderer cleanup. The normal application's baseline server was absent before and after testing; we did not test against the owner's working installation.

The shell PID and directory survived resize, zoom, and reattachment. We fixed gutter expansion on a larger reattached client and verified that all reserved bands returned to two cells. At 209×49 window cells, the shell has 203×43 cells: gutters and separators reserve 14.76% of the area. This is a prototype cost, not a recommended full-layout allocation.

Scoped compositor key events reached an isolated byte recorder. A compositor-driven mouse drag selected the exact fixture text `BORDER_SELECTION_OK` through tmux. Captures showed test text clear at all four shell corners. Two zoom/unzoom recoveries used the same two image IDs. Terminating the renderer removed the frame; scoped stop preserved a separate guard server. Concurrent launchers left one intact five-pane probe, and controls refused an unmarked session and the baseline socket.

We rendered the legacy upstream CSS in Chromium at the prototype's 1881×980 pixel canvas, using its 9×20 cell geometry for placement. The port's raster and the CSS reference had 99.96% intersection-over-union of border-pixel support, using a 12-level RGB-distance threshold from the background. This compares the isolated contour, not the full upstream application or every antialiased pixel.

Twenty gutter captures over a 5.515-second idle interval were identical; the renderer emitted zero bytes during that interval. The renderer plus its waited-for tmux clients used about 6.35% of one CPU core, excluding the tmux server, Kitty, and GPU. The polling overhead and gutter cost need attention before full-layout integration. Sampling does not rule out shorter glitches, and only one attached client was tested.

### Review and polling cost

On 2026-10-25, we replaced five tmux processes per idle cycle with one format snapshot containing visibility, client identity, shell geometry, and gutter dimensions. The renderer still polls twice per second. It resizes only bands with incorrect dimensions and uploads graphics only for initialization or changed state.

In a same-VM comparison of 40 idle cycles, the previous query path used 611 ms of CPU time and the snapshot path used 123 ms, including waited-for child processes. That is about an 80% reduction for the query path. The visible reviewed renderer used about 1.0% of one core over 12 seconds. This measurement excludes the tmux server, Kitty, and GPU; it does not measure end-to-end application overhead.

The final guest suite passed 34 Python tests and the Lua assertions in about 20 seconds. New tests cover the single-query contract, visibility, malformed snapshots, gutter mutations, and exact stop targeting. The normal launcher's stop now targets `=edex` so it cannot prefix-match the probe's session. The client test fixture terminates its owned client before waiting instead of spending three seconds waiting for a client that remains attached.

We inspected the reviewed border in Kitty and exercised resize and zoom/unzoom. The native shell PID survived and the gutters returned to two cells. The frame remains a standalone, single-client experiment. The normal five-shell layout still uses its previous borders.


## Full-layout integration target

Kitty documents [relative image placements](https://sw.kovidgoyal.net/kitty/graphics-protocol/#relative-placements) that can follow a Unicode-placeholder parent. Test a frame anchored to the existing tab header, with transparent pixels over the shell and drawing confined to reserved gutters. Follow the upstream main_shell.css bottom-left and top-right clipped contours.

Keep native shell input, selection, and tmux mouse behavior. Update the frame on layout changes; static borders need no animation loop.


## Checks before merging

- Compare a reference frame with the prototype at the same viewport and cell size. Measure the gutter cost.
- Resize, zoom, switch shell tabs, show and hide the keyboard, detach, and reattach. Check hidden anchors and stale images.
- Test mouse selection, pane resizing, and shell text near the corners. Decorations must not cover text or consume input.
- Sample static regions for flicker using stable image and placement IDs. Measure idle CPU and transport volume.
- Test two clients with different dimensions, or document a supported single-client limit with evidence.
- Run the existing tests. Show captures and record failures before proposing a default change.

The standalone prototype does not replace borders in the normal layout. Full-layout integration and the checks involving shell tabs, the keyboard, and multiple clients remain prerequisites for any default change.
