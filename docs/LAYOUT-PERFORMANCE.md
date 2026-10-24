# Layout, dividers and overhead review — 2026-10-24

Scope: disposable Omarchy VM only. Native shell processes and normal user configurations were preserved.

## Terminal tabs

The pinned upstream main_shell.css specifies normal inherited text size (16px), 0.7vh top padding, 0.4vh bottom padding and skewX(35deg). The old port stretched the artwork to a three-row/60px pane and enlarged the label. The corrected strip uses a 19px line box plus 1.1vh padding (about 30–31px at the reviewed height), 16px labels and a matching 35-degree hit-test geometry. A two-row tmux pane reserves 40px because terminal cells cannot reserve fractional rows; unused pixels stay background. The extra native pane-title row is disabled. This corrects dimensions without claiming exact font equivalence.

Reference: [pinned original shell CSS](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/assets/css/main_shell.css), also retained under references/css/.

## Pane dividers

The original main shell uses augmented-ui bl-clip/tr-clip contours, a 0.18vh border at half opacity and a separate tab rule. Its side columns primarily use interrupted module rules rather than a generic heavy rectangular frame.

[tmux's documented pane borders](https://man.openbsd.org/tmux.1#pane-border-lines) offer predefined character line styles, colors and optional title rows. They cannot specify arbitrary pixel contours, border thickness in pixels or true alpha blending. Current deployment uses consistent subdued single lines, matching active/inactive colors, no redundant title row, and the original-style pixel rules inside our instrument canvases. Native mouse resizing and pane boundaries remain functional.

A faithful clipped frame is feasible inside a renderer-owned Kitty canvas. A frame around an ordinary shell would need reserved drawing gutters or a separate decoration surface; it cannot be obtained by a tmux color setting alone. That extension has not been implemented here. Do not place a decorative overlay over shell content or replace the shell with a custom emulator simply to draw corners.

## Can existing tools replace collection or visualization?

The VM has btop and ps. Glances, sysstat tools and psutil were not installed at inspection. No documented structured metrics export was found in the btop README checked; running its TUI would also bring its own layout rather than reproduce the original instruments. Scraping its screen is not a suitable data contract. This is not a claim that a future btop integration is impossible.

[Glances](https://glances.readthedocs.io/en/latest/api/restful.html) does expose structured metrics. Reusing an already-running instance could make sense if one exists later. Starting a new collector/API service just for these two panes has not been shown to lower overhead, and none was installed. ps exposes useful process data, but its default CPU percentage is not the same contract as the port's interval counter deltas; substituting it without adapting those semantics would change the displayed meaning.

The current collector already reads kernel counters directly once per second. Measured collector CPU time was roughly 7–11ms/sample in the VM. By contrast, render/encode runs up to 24 times per second. cProfile identified PNG encoding and globe projection/polygon drawing as the large costs. Merely replacing the collector would therefore leave the dominant work in place.

Implemented improvement: use Kitty's [documented zlib-compressed RGB format](https://sw.kovidgoyal.net/kitty/graphics-protocol/#compression), backed by the existing native Pillow/zlib libraries. It preserves every pixel and avoids PNG filtering. In one same-process fixed-geometry comparison, median render/encode CPU times were System 7.448ms PNG versus 5.348ms RGB, Network 17.752ms versus 14.413ms. Compressed payloads averaged 35,963 versus 31,066 bytes and 47,368 versus 37,217 bytes respectively. These are microbenchmarks, not end-to-end refresh-rate guarantees; VM load and globe orientation affect results.

Idle tab/keyboard geometry queries are capped at twice per second, keyboard client-list polling at once per second; input reads remain responsive independently. Graphics animation continuation packets retain a=f as required by the protocol. Future work should target cached static layers and native/batched globe rendering, then consider sharing one collector between existing processes if the number of instruments grows. Those additional backend changes are proposals, not installed features.

Reproduce profiling with `python3 profile_panes.py`. It measures only this project's pane processes, excludes descendants/Kitty/tmux from pane CPU percentages, and separately compares CPU-time microbenchmarks. No helper service is left running.

## Flicker investigation

An 8-second actual-desktop capture found two frames in which all three static probe regions (System heading, Network heading and tabs) went blank together. Those regions exclude graph motion and the clock. This distinguishes repaint blanking from uneven animation.

Previously the one-second placement heartbeat alternated placement IDs and rewrote every placeholder cell. It now preserves IDs and sends placement metadata only. Placeholder cells are committed in a synchronized-output block only for initialization/actual recovery; root texture updates remain continuous. Tab bootstrap retransmission updates the existing root rather than recreating it. The 24 FPS target was retained.

The first post-fix capture sampled 173 frames over 12 seconds with identical nonzero static-region ink counts throughout. A second capture after zoom/restore, tab and keyboard interactions sampled another 241 frames over 16 seconds, again with identical nonzero counts. Total: 414 post-fix samples over about 28 seconds, with no blank static regions. Zoom/restore also recovered visibly. Capture sampling can miss shorter glitches; this is bounded evidence rather than a universal no-flicker guarantee. The VM guest capture also cannot establish the behavior of every host display/compositor path.
