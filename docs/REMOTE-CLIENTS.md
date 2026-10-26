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

The launcher uses your current terminal, sends direct graphics through SSH and requires no server display or KITTY_WINDOW_ID. Recognized xterm-kitty SSH sessions select this route without --in-place. For another compatible client, request it with --in-place without changing TERM. Use an interactive PTY, outside another tmux session, with at least 140 columns by 40 rows. For a command supplied to SSH, request a PTY with ssh -t.

The renderer needs direct image data, Unicode placeholder placements and root animation-frame updates. Basic image support alone does not establish compatibility. The in-place path does not apply the dedicated window's font or static dotted background. It rejects tempfile graphics because the client cannot read server paths.

The attach command declares RGB and underline-color support for this graphics client. Placeholder image/placement IDs use those colors; tmux must preserve them even when a compatible mobile client advertises xterm-256color. This declaration does not change TERM or modify your normal tmux server.

Direct clients use a separate per-user socket ending in -direct. An explicit EDEX_TMUX_SOCKET overrides it. Use the same entry point and selector for controls. Local desktop shells remain separate; the launcher must not attach a remote client to their tempfile session. The 8/12 FPS options reduce work for a new session; 24 remains the default. Reattaching does not change existing worker arguments.

## La Terminal on iPadOS

La Terminal uses SwiftTerm, whose current upstream documents PNG/raw Kitty images, Unicode placeholders and animation frames. The shipped app version and connection transport determine what reaches its renderer. See [La Terminal](https://la-terminal.net/), [its release history](https://apps.apple.com/app/id1629902861) and [SwiftTerm's graphics documentation](https://github.com/migueldeicaza/SwiftTerm/blob/main/Sources/SwiftTerm/Documentation.docc/KittyGraphicsProtocol.md).

On 2026-10-27 the owner tested the installed iPad client against server-side probes. Neither Kitty PNG nor Sixel appeared over Mosh. Both appeared over plain SSH. A separate direct-transfer probe then displayed placeholders and a moving root-frame update over SSH. We did not record the app version. These observations cover the tested primitives, not full-interface performance, touch, resize or reconnect behavior.

Use plain SSH for this path. Mosh emulates and synchronizes terminal state instead of forwarding a raw stream; the launcher fix does not add Mosh graphics support. See [the Mosh protocol paper](https://mosh.org/mosh-paper-draft.pdf). Do not change TERM to disguise an unsupported transport.

## Validation

The full Ubuntu runtime suite and Debian package checks passed. Tests cover argument boundaries, missing display variables, direct-transfer enforcement, session isolation, non-PTY rejection and controls. A real Omarchy SSH PTY test passed launch and keyboard creation without a display or KITTY_WINDOW_ID, and preserved the test shell PID.

The multipart sender now uses m/q continuation fields, plus a=f for animation data. Image/frame metadata appear on the first packet, as required by [Kitty's protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/#transferring-pixel-data). This correction does not prove a fix for the reported local globe flash. Direct-transfer reattach and multiple-client behavior still need stress testing.
