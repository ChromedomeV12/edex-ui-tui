# Remote launch and mobile clients

This guide covers the unreleased fix/launch-routing branch. The published alpha opens a new Kitty window on the server, which can fail over SSH with `X11: The DISPLAY environment variable is missing`. Installing Kitty on the server does not provide a display to a remote session.

From a checkout of this branch in a compatible client:

```sh
python3 app.py --in-place --fps 8
python3 app.py --in-place --toggle-keyboard
python3 app.py --in-place --install-shell-frame
# Finish shell work before stopping; this ends the project's shells:
python3 app.py --in-place --stop
```

The launcher uses your current terminal, sends direct graphics through SSH and requires no server display or KITTY_WINDOW_ID. Recognized xterm-kitty SSH sessions select this route without --in-place. For another compatible client, request it with --in-place without changing TERM. Use an interactive PTY, outside another tmux session, with at least 120 columns by 40 rows. For a command supplied to SSH, request a PTY with ssh -t.

For the whole dashboard on an iPad, use landscape, hide the system keyboard and reduce terminal text size until stty size reports at least 40 rows and 120 columns. The owner chose this full-layout approach after a 21-row/98-column launch failed. We checked launch, resize and keyboard toggles at 120×40 and 130×42, preserved native shell PIDs, and inspected a 130×42 graphical window. Narrow process rows shorten names before numeric values. The error now includes the measured size. The published alpha retains its old 140×40 guard.

The renderer needs direct image data, Unicode placeholder placements and root animation-frame updates. Basic image support alone does not establish compatibility. The in-place path does not apply the dedicated window's font or static dotted background. It rejects tempfile graphics because the client cannot read server paths.

The attach command declares RGB and underline-color support for this graphics client. Placeholder image/placement IDs use those colors; tmux must preserve them even when a compatible mobile client advertises xterm-256color. This declaration does not change TERM or modify your normal tmux server.

Direct clients use a separate per-user socket ending in -direct. An explicit EDEX_TMUX_SOCKET overrides it. Use the same entry point and selector for controls. Local desktop shells remain separate; the launcher must not attach a remote client to their tempfile session. The 8/12 FPS options reduce work for a new session; 24 remains the default. Reattaching does not change existing worker arguments.

## Bottom-panel choices

Choose panels when creating a new session with --bottom:

| Value | Bottom area | File browser starts? |
| --- | --- | --- |
| files | Files, keyboard hidden (default) | Yes |
| keyboard | Full-width keyboard | No |
| both | Files beside the keyboard | Yes |
| none | No bottom panels | No |

For the removable user preview:

```sh
edex-ui-tui-preview --bottom keyboard
```

From a source checkout, use python3 app.py --in-place --bottom keyboard. The --files option selects the browser program only when files are visible. A fresh keyboard-only or no-bottom session does not start navigator.py or Yazi.

Ctrl-b then Shift-K, or --toggle-keyboard, switches files↔both and keyboard↔none. Hiding a keyboard preserves its process and the native shell. The keyboard fills the bottom width when no file pane exists. Changing the startup selection of an existing session returns an explanation instead of closing a browser or shell. Finish work and stop that session before choosing a different startup mode, or use a separate EDEX_TMUX_SOCKET.

We tested all four modes at 120×40, toggled each twice and checked shell PIDs and pane health. Resize tests cover keyboard-only and no-bottom layouts. A 130×42 graphical review confirmed the full-width keyboard with no browser pane.

## La Terminal on iPadOS

La Terminal uses SwiftTerm, whose current upstream documents PNG/raw Kitty images, Unicode placeholders and animation frames. The shipped app version and connection transport determine what reaches its renderer. See [La Terminal](https://la-terminal.net/), [its release history](https://apps.apple.com/app/id1629902861) and [SwiftTerm's graphics documentation](https://github.com/migueldeicaza/SwiftTerm/blob/main/Sources/SwiftTerm/Documentation.docc/KittyGraphicsProtocol.md).

On 2026-10-27 the owner tested the installed iPad client against server-side probes. Neither Kitty PNG nor Sixel appeared over Mosh. Both appeared over plain SSH. A separate direct-transfer probe then displayed placeholders and a moving root-frame update over SSH. We did not record the app version. These observations cover the tested primitives, not full-interface performance, touch, resize or reconnect behavior.

Use plain SSH for this path. Mosh emulates and synchronizes terminal state instead of forwarding a raw stream; the launcher fix does not add Mosh graphics support. See [the Mosh protocol paper](https://mosh.org/mosh-paper-draft.pdf). Do not change TERM to disguise an unsupported transport.

## La Terminal 2.0.10 issues

The owner reports that tapping the custom keys opens the iPad system keyboard. The finger-toggle instructions in the legacy documentation do not match this app version. We have not verified a current client setting that prevents the popup; the server cannot dismiss an iPad input view. Keep this as an open client-compatibility issue. Do not treat mouse reporting alone as proof that native keyboard behaviour works.

For clients that display images vertically inverted, the new-session --flip-images-y option reverses transmitted image rows. It covers PNG and compressed RGB/RGBA, preserving alpha, dimensions, placements and input coordinates. It remains off by default and adds decode/re-encode work on that client path. It does not alter the client's terminal text or other programs' images. Test on the affected client before claiming visual correction.

The owner confirmed on 2026-10-27 that all preview images are upright on La Terminal 2.0.10 after enabling this correction. The native keyboard popup remains open and deferred; no keyboard-input behaviour changed in this fix.

Use a separate socket for this orientation instead of changing workers in an existing session:

```sh
EDEX_TMUX_SOCKET=edex-ipad-fixed edex-ui-tui-preview --bottom keyboard --flip-images-y
```

Detach the previous view before this test so only one session animates. Its native shell remains alive. New keyboard workers inherit the orientation setting. Reattaching the corrected session retains it; attempting to apply the flag to an uncorrected live session returns an explanation rather than changing unrelated workers.

## Validation

The full Ubuntu runtime suite and Debian package checks passed. Tests cover argument boundaries, missing display variables, direct-transfer enforcement, session isolation, non-PTY rejection and controls. A real Omarchy SSH PTY test passed launch and keyboard creation without a display or KITTY_WINDOW_ID, and preserved the test shell PID.

The multipart sender now uses m/q continuation fields, plus a=f for animation data. Image/frame metadata appear on the first packet, as required by [Kitty's protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/#transferring-pixel-data). This correction does not prove a fix for the reported local globe flash. Direct-transfer reattach and multiple-client behavior still need stress testing.
