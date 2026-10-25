# Validation

## Reviewed setup

We reviewed the interface in a disposable Omarchy VM on 2026-10-24: Kitty 0.49.2, tmux 3.8, Yazi 26.9.1, Python 3.14, and Pillow 12.3. We used an earlier prototype on Ubuntu 24.04 with Kitty 0.32.2 and tmux 3.4. We have not propagated the current finishing pass to Ubuntu.

The checks cover graphics packet framing, stable placement metadata, RGB transport, renderer geometry, tmux timeout recovery, shell switching, keyboard taps, and Yazi navigation. Run `python3 tests/run.py` from the root to reproduce them. Integration checks use private servers, temporary files, and input recorders. They do not exercise your live shell.

## Visual and interaction checks

We inspected desktop captures after startup, shell zoom/restore, tab switching, keyboard display, and file navigation. The owner accepted the instrument motion as smooth enough. We reproduced static-region blanking in 2 of 125 samples before the heartbeat fix. After the fix, we captured 414 samples across about 28 seconds with no blank static regions. Sampling can miss shorter glitches and does not establish behavior on other terminals or display paths.

We measured 1,682 system frames and 1,667 network frames over a 70-second run. Those counts measure frame production, not screen refresh. In a fixed-geometry microbenchmark, median render/encode CPU time fell from 7.448 to 5.348 ms for System and from 17.752 to 14.413 ms for Network after switching from PNG encoding to compressed RGB. We have not compared total resource use with Electron.

The Yazi integration test covers grid movement, paging, empty directories, parent navigation, click-only selection, file activation through a recording opener, marks, filtering, wheel movement, and resize calculations. The keyboard test sends synthetic mouse events through a private tmux client into a raw-byte recorder.

## Limits

### Grid, frame and popup experiment (2026-10-25)

We inspected the grid preset in the same disposable Omarchy VM against upstream screenshots and the owner's v2.2.8-pre reference. The tile shows behind instrument and keyboard artwork, file cards and shell-frame padding; the native shell and tab faces remain solid. An app-scoped compositor opacity override removed the desktop wallpaper showing through the shell. The launcher does not install that override.

The full Python/Lua suite passed at the integration checkpoint. After the popup fixes, focused checks passed eight background/frame contracts and two popup contracts, including close/reopen, duplicate opens, shell PID/cwd preservation, initiating-pane focus, blocked on-screen input and restoration of masked frame pixels. We inspected real captures with the popup open and closed. A raw graphics alpha update was necessary to clear covered frame strokes; re-transmitting under the same image ID left stale strokes in the first attempt.

In the review session we exercised resize and restore, shell zoom/unzoom, a round trip through shell slot two, and keyboard hide/show. The original shell PID survived, the padding returned to one row, and a settled desktop capture showed both columns, keyboard and clipped frame. These checks do not establish flicker-free transitions. Reattach with the grid preset was checked before frame integration; full-frame reattach, resizing an open popup and differing clients remain unverified. The stored grid uses an integer 1080px reference tile, not arbitrary-resolution CSS rasterization. No Electron performance comparison has run.

We have not verified physical touchscreen input, iOS/Android SSH clients, Mosh graphics transport, complete boot choreography, audio, all upstream effects, or pixel-perfect equivalence. Physical typing does not trigger keyboard highlights. We use an open font approximation. Border experiments remain separate from main.

We excluded old capture collections and local manifests from this repository. The README includes an owner-supplied Omarchy VM screenshot and a keyboard renderer preview. The VM screenshot shows the interface before the repository extraction, so its file listing uses the earlier folder layout.
