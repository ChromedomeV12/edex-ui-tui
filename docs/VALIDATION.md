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

We inspected the grid preset in the same disposable Omarchy VM against upstream screenshots and the owner's v2.2.8-pre reference. The tile shows behind instrument and keyboard artwork, file cards and the space outside the terminal contour. The later corner fix makes the terminal inset solid; the native shell and tab faces remain solid. An app-scoped compositor opacity override removed the desktop wallpaper showing through the shell. The launcher does not install that override.

The full Python/Lua suite passed at the integration checkpoint. After the popup fixes, focused checks passed eight background/frame contracts and two popup contracts, including close/reopen, duplicate opens, shell PID/cwd preservation, initiating-pane focus, blocked on-screen input and restoration of masked frame pixels. We inspected real captures with the popup open and closed. A raw graphics alpha update was necessary to clear covered frame strokes; re-transmitting under the same image ID left stale strokes in the first attempt.

In the review session we exercised resize and restore, shell zoom/unzoom, a round trip through shell slot two, and keyboard hide/show. The original shell PID survived, the padding returned to one row, and a settled desktop capture showed both columns, keyboard and clipped frame. These checks do not establish flicker-free transitions. Reattach with the grid preset was checked before frame integration; full-frame reattach, resizing an open popup and differing clients remain unverified. The stored grid uses an integer 1080px reference tile, not arbitrary-resolution CSS rasterization. No Electron performance comparison has run.

We have not verified physical touchscreen input, iOS/Android SSH clients, Mosh graphics transport, complete boot choreography, audio, all upstream effects, or pixel-perfect equivalence. Physical typing does not trigger keyboard highlights. We use an open font approximation. Border experiments remain separate from main.

We excluded old capture collections and local manifests from this repository. The README includes an owner-supplied Omarchy VM screenshot and a keyboard renderer preview. The VM screenshot shows the interface before the repository extraction, so its file listing uses the earlier folder layout.

## Palette and compatibility pass (2026-10-25)

We kept the native top popup at the owner's request and removed the custom process-table experiment. Its frame mask tracks the opening rectangle only. We do not claim correct occlusion during dragging, popup resize, or use by several clients.

The shared palette reads the pinned tron.json: primary #aacfd1 and background #05080d. We checked memory point states against mod_ramwatcher.css: free 10%, available 30%, active 100%. The dedicated terminal's ANSI slots follow terminal.class.js's grayscale-and-mix fallback. These colors apply to this application's Kitty config, not the owner's general terminal theme. The palette tests compare the config with the derived slots and CSS blends.

We ran the Linux integration suite on Ubuntu 24.04 with Kitty 0.32.2, tmux 3.4, Python 3.12 and Pillow 10.2. The first copy contained CRLF config lines; tmux 3.4 rejected the option values. The LF copy passed. The repository specifies LF through .gitattributes.

A Windows-side capture of the WSLg Kitty window showed both instrument columns, the shared dots, opaque central shell and clipped terminal frame. The minimal test distro needed libwayland-cursor0 and libwayland-egl1 to start Kitty, and librsvg2-bin for original Yazi icons. Its graphics logs report EGL/driver warnings, so this setup does not establish native GPU performance. Physical touch and mobile clients remain untested.

The profiler now groups the selected tmux server, its descendants, attached clients and their Kitty ancestor. It skips empty padding panes and checks process start times before attributing CPU deltas. Its summed RSS includes shared pages more than once; it misses CPU from short-lived processes between snapshots and excludes compositor/GPU/WSLg work. Keep these results separate from a controlled Electron comparison.

### Reattach and local transfer

The finishing pass reproduced blank live panes after a fresh Kitty client attached. Their placeholder cells remained present. A probe that owned its own input captured Kitty decompression and zero-dimension errors during multipart transfers; no graphics replies entered an interactive shell. We removed that probe from the implementation.

The experiment adds `--graphics-transport tempfile` for local Kitty launches. Each image uses one short protocol command referencing a private temporary file. Kitty reads and deletes that file. The sender bounds outstanding files to 128 per image and removes its remaining files on image cleanup. Unit checks cover private permissions, one packet per frame, terminal-side consumption and cleanup without touching unrelated files. This mode requires a shared filesystem. Direct transfer remains the default and needs further reattach stress testing for SSH use.

The frame fix delays the relative child until the tab image completes its bootstrap repaint. Its steady heartbeat refreshes placement metadata without uploading pixels. Geometry, parent and popup-mask changes replace only the frame's owned image root. We inspected renderer restart, fresh-client reattach and native top popup closure in Omarchy. Eleven background/frame checks cover the resulting contour and recovery contracts.

The final source passed 52 Python tests and the Lua grid checks in both reviewed distros. The Omarchy local-transport capture after a fresh client showed System, Network, Yazi, keyboard and the main frame together. Ubuntu's clean local-transport run kept those workers alive through frame installation and keyboard layout changes. The empty frame-padding pane has no worker and is not a failed instrument.

One eight-second Omarchy diagnostic sample reported 129.74% of one CPU core across the selected process groups and 539.84 MiB of summed RSS. No selected process appeared or exited between its snapshots. The review VM and WSLg shared the host, and this is one sample, not a performance comparison or release budget. We have not established an improvement over Electron.

A further stalled-consumer test checks the 128-file limit and cleanup; it passed separately.

### Keyboard size and arrow alignment

The 2026-10-25 keyboard pass enlarges its open pane and lower strip without stretching the measured layout. We center the Up key over Down and center the four SVG icons within their hit rectangles. The drawing and input paths share these adapted rectangles. We leave the source measurements intact for comparison.

Geometry tests cover four canvas sizes and all three legend states. The synthetic touch test routes the arrow commands through a private tmux client to a byte recorder. A layout integration test opens and hides the keyboard twice, checks file-area restoration and tab-strip height, and verifies that both shell and keyboard PIDs remain unchanged. We inspected the larger keyboard in the live Omarchy review window. Physical touch remains untested.

Rapid hide/show initially cleared the tab-image placeholders even when the renderer observed the same final pane size. The launcher now marks completed keyboard layout changes with a session revision. The tab renderer repaints once for that revision and retains metadata-only heartbeats between changes. We inspected the recovered tabs and shell frame after rapid toggles. The full suites passed on Omarchy and Ubuntu; the frame and workspace checks passed again after this recovery adjustment.

### Instrument typography and row bounds

The next pass corrects the network status grid to the upstream 1:2:1 proportions and bounds each process-table field. CPU and memory values align to their column's right edge. We reduced fixed font-size floors so metadata can fit short columns, and removed a premature CPU-model character limit in favor of measured text fitting.

The regression test records glyph bounds at 350x680, 260x500 and 220x420 pixels. It checks percentage-column separation, uptime label/value separation and full-length IPv4 rendering. The full suites passed on Omarchy and Ubuntu. We inspected synthetic size comparisons and live Omarchy captures; see [the visual audit](VISUAL-AUDIT.md) for remaining resize and font limitations. The Windows run encountered sandbox temporary-directory permission failures in two existing fixture tests; those tests passed in the Linux suites.

### Repeated local performance samples

After warm-up, we took three consecutive ten-second samples of the Omarchy review session at 209x49 cells with both instrument columns, native idle shells, Yazi, tabs, frame and keyboard visible. The workers target 24 FPS. These samples cover the selected process groups, not compositor or GPU cost.

| Sample | CPU, percent of one core | Summed RSS, MiB |
| --- | --- | --- |
| 1 | 141.90 | 563.84 |
| 2 | 145.99 | 563.84 |
| 3 | 133.80 | 563.84 |

The median total was 141.90% of one core. Session descendants accounted for 113.30% to 126.09%; Kitty accounted for 17.30% to 18.60%. Shared pages contribute to several RSS totals, and the snapshot method misses short-lived processes. The earlier eight-second sample used a different session state, so it does not establish a before/after improvement or regression.

The profiler's separate 12-frame CPU microbenchmarks reported network-column zlib/RGB median render-and-encode times of 28.45 to 34.02 ms and system times of 10.87 to 16.96 ms. These benchmarks render fixed-size synthetic frames after each idle sample; they do not measure displayed frame pacing. Profile the globe drawing and raster/transfer path next. We have not set or met a release performance budget, completed a long soak, or compared against Electron.
