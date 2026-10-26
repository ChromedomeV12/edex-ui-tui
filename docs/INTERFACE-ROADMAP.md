# Interface roadmap

## Next prerelease: native cost and remote launch

The first alpha is published. Prioritize the SSH entry-point fix and multipart protocol correction on fix/launch-routing, then the static-layer and dirty-rectangle work in [the native older-laptop checkpoint](NATIVE-LOW-END.md). Keep 24 FPS as default and 8/12 as opt-in lower-rate targets. Measure equal-quality savings before choosing a higher rate.

The owner's La Terminal probes pass Kitty images, placeholders and root-frame animation over SSH but fail through Mosh. Read [remote-client guidance](REMOTE-CLIENTS.md). Full mobile input, reconnect and bandwidth checks remain. The native globe flash also remains open; do not count a framing change as visual verification.

Research snapshot: 2026-10-25. The experiment branch now includes a grid preset, a tab-anchored clipped shell frame and a native process-details popup. Main keeps the reviewed baseline. The remaining items below describe acceptance work and later features.

## First priority: keyboard size and alignment

Enlarge the optional keyboard before continuing the remaining visual checks. Give it 62% of the lower strip's width and increase that strip from 30% to 36% of the window height while the keyboard is open. Restore the file pane's height when hiding it. Preserve uniform scaling, row stagger and the two-piece Enter key. Center Up over Down and center the arrow artwork inside each hit region. Check normal, Shift and Fn states, synthetic taps, small windows and a live Omarchy capture before closing this item.

Implemented and reviewed on 2026-10-25. At the reviewed 209-column by 49-row size, the keyboard grows from 115 by 14 cells to 129 by 17 cells, increasing its uniform drawing scale by about 23%. Geometry checks cover four canvas sizes and normal, Shift and Fn states. Synthetic taps pass; repeated toggles preserve the shell and keyboard processes, restore the file area and retain the tab strip's height. The live Omarchy capture confirms the larger layout and aligned arrows. Continue the remaining upstream typography and state-color checks below.

## 1. Restore the upstream dotted background

The pinned eDEX main.css defines two crossed linear gradients over the theme's grey. Each dark band occupies 1.85vh of a 2.04vh period. Their intersections leave small square dots. The tron theme uses #05080d for light_black and #262828 for grey. At a 1080px viewport, the period is about 22px and the dots are about 2px wide. Centering and fractional pixel coverage affect the exact phase and edge pixels.

The upstream renderer toggles the solidBackground class during its title sequence and clears it before the main UI. Our boot.py draws a simplified point grid during parts of startup. The experiment's kitty-grid.conf now uses a native tiled image, while kitty.conf retains the solid fallback. The current stored tile targets a 1080px viewport; it does not reproduce fractional CSS phase at arbitrary resolutions.

Start with a static tile generated from those CSS dimensions and colors. Test Kitty's native tiled background in a project-specific configuration. Generate the tile for the reviewed viewport, and compare it against a browser-rendered CSS reference. Regenerate on viewport changes only if the comparison shows a material difference. A static background needs no frame loop or metric collector.

### Screenshot layer reference

We inspected the pinned upstream `media/screenshot_default.png` and `media/screenshot_blade.png` on 2026-10-25. The owner then supplied a clearer TRON screenshot showing eDEX v2.2.8-pre. Use that image as the primary visual reference and the pinned CSS to explain the layers. It shows dots in the padding inside the clipped shell frame, including the strip beneath the opaque terminal viewport. During the later corner review, the owner requested that the terminal inset stay solid. The current experiment follows that request and keeps the dots outside the closed terminal contour. This differs from the upstream padding. Keep Blade only as a cross-check for surface boundaries. The owner's attachment remains outside the published repository.

| Region | Dotted background visibility |
| --- | --- |
| Outer margins and space between modules | Visible as one shared field |
| System column, clock, telemetry and process list | Visible behind the content |
| CPU charts | Visible behind the curves; cpuinfo.class.js sets the chart grid fill and stroke to transparent |
| Network column, globe surroundings and traffic chart | Visible behind the content; the globe and graph strokes cover their own pixels |
| Filesystem icon area and gaps around captions | Visible; icons, scrollbar and interaction fills cover their own pixels |
| Keyboard, gaps, spacebar and outlined Enter interior | Visible in the idle state; letters and outlines cover their own pixels |
| Pressed keys and file interaction feedback | Apply the upstream state fill; preserve the background beneath it for release |
| Central terminal viewport | Solid dark surface, including unused space below shell output |
| Tab faces | Solid dark inactive faces and solid cyan active face |
| Modal body | Solid dark surface, confirmed in modal.css |

The grid preset uses transparent side-column and keyboard canvases over Kitty's shared tile, with solid shell and tab faces. Keep terminal opacity changes within this application's Kitty launch. Verify the transparent animation frames in the guest before treating this experiment as complete.

Screenshot sources: [default TRON](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/media/screenshot_default.png), [Blade](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/media/screenshot_blade.png).

Check default terminal backgrounds, explicit RGB cell backgrounds, tmux separators, and our opaque instrument rasters. Matching RGB values do not guarantee that Kitty treats a cell as the default background. Avoid a pattern that disappears in one pane or restarts its phase at every divider. If a native tile cannot preserve the intended layers, draw the shared pattern into renderer-owned surfaces using their window-relative origin and cache the static layer. Keep the native shell readable and respect application-supplied backgrounds.

Acceptance:

- Match dot size, pitch, color, and phase at the reference viewport; inspect a second size and font scale.
- Inspect startup transitions, shell text, selection, Yazi captions, gutters, and zoom/restore.
- Measure idle writes and CPU. Do not add periodic background retransmission.
- Keep the option local to this application, with a solid-background fallback.

Sources: [main.css](../references/css/main.css), [tron palette](../references/tron.json), [pinned title sequence](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/_renderer.js), and [Kitty background configuration](https://sw.kovidgoyal.net/kitty/conf/#opt-kitty.background_image).

## 2. Bring back useful pop-out views

The upstream Modal class creates in-application panels with a title, clipped border, buttons, focus handling, and close feedback. Users can drag the title with a mouse or touch. We confirmed these callers in the pinned source:

| Upstream action | Upstream view | Proposed terminal implementation |
| --- | --- | --- |
| Click Top Processes | Active Processes table, sortable columns, live updates | A scoped tmux popup containing an existing process viewer, or a small table backed by the existing Linux counters |
| Search the current directory | Fuzzy cwd file search | Yazi's search integration or fzf in a popup, scoped to the browser's directory |
| Open a text file | Editable text with Save to Disk | Existing editor in a popup; preserve explicit save/discard behavior |
| Open images, audio, or video | Media panel and playback controls | Use existing preview/player tools; test graphics in a popup before promising image/video support |
| Open a PDF | Page navigation and zoom | Use an existing reader/preview backend with bounded rendering and page controls |
| Open settings or shortcuts | Settings/help panel | A native tmux menu or text popup showing actual controls |

The upstream keyboard's detach() toggles its link to terminal input while a dialog owns focus. It does not detach a visible keyboard pane. In this port, the keyboard currently targets only the central shell. The first popup milestone should keep that contract and prevent input leaking to the shell. Adding popup keyboard support requires an explicit, scoped input-target change and recorder tests.

We found modal detail views, not evidence that each original instrument can become an independent OS window. Keep that distinction in implementation claims. Treat lifting an existing tmux pane into another window as a separate optional feature.

### Start with a process-details popup

The owner chose to keep the existing procps top popup rather than continue the custom process-table renderer. The experiment opens procps top in a native tmux popup through Ctrl-b then Shift-P or a click on the system column's process list. The viewer starts on demand. A socket-scoped lock rejects duplicate opens; an input guard blocks on-screen keys from reaching the shell while the popup owns focus. The clipped frame masks only the popup rectangle and restores its covered strokes after closure. This first popup uses tmux's rectangular border; custom clipped modal artwork remains future work.

Use the installed tmux display-popup command first. Give the popup a functional title, cyan frame, mouse/keyboard focus, and a close path that restores the source pane. Create its process only when opened and stop its updates when closed. Reuse a process viewer before building another process manager. Do not open duplicate details windows for repeated activation of the same module.

Use argument-vector subprocess calls for file paths and commands. Do not interpolate filenames into shell or tmux format strings. Preserve Yazi's accepted Enter behavior; expose preview through a separate action rather than changing it without review.

The guest's tmux command inventory includes display-popup. Its inventory did not include new-pane, despite newer upstream documentation describing floating panes. Feature-detect the installed binary instead of relying on its version string. Do not upgrade the VM to gain a new command as part of this experiment.

Check whether this binary updates underlying instrument panes while a popup is open. Test popup cleanup and reinitialization of Kitty images before decorating it with pixel graphics. A native rectangular frame is an acceptable first functional prototype; clipped corners can follow once focus, closure, and redraw work. Native pane pop-out and return can use break-pane/join-pane later, preserving PID, cwd, slot mappings, and keyboard target.

Acceptance:

- Open, close, and reopen without changing the central shell's input or cwd.
- Restore focus; preserve terminal input and selection. Verify that Escape, application quit, and process exit have defined behavior.
- Resize and reattach with the popup open. Check graphical occlusion, stale images, and underlying update behavior.
- Start no popup worker or polling loop while closed. Compare process count and CPU before, during, and after use.
- Use a recorder for keyboard routing, including the optional on-screen keyboard. Do not test by executing characters in a live shell.

Sources: [pinned Modal implementation](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/classes/modal.class.js), [process details](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/classes/toplist.class.js), [file viewers](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/classes/filesystem.class.js), [search](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/classes/fuzzyFinder.class.js), and the installed tmux manual and command inventory.

### Other terminal projects reviewed

We inspected source snapshots on 2026-10-25. These are design references, not added runtime dependencies. We have not copied their source code.

| Project and snapshot | Relevant implementation | Application here |
| --- | --- | --- |
| Workmux, 3cef212252896a9d69d01cc946a95d6cbf25978f | Its dashboard documentation uses native tmux display-popup -E. Its shared Ratatui popup renderer clears the popup region before drawing; centered_rect clamps to the available area. Its tmux backend resolves pane/session identity without treating a popup process as the owner of the underlying pane. | Keep the native tmux popup, clamp dimensions, preserve the initiating focus and cwd, and identify persistent shells by pane ID. Do not assume that clearing text cells also clears a Kitty image. |
| TUIOS, 42084d968e7d2db2438abe4aa1378a3de35954ca | os_popup.go computes popup bounds against each client's content region. popup_test.go excludes temporary popups from normal window cycling and covers resizing. kitty_occlusion.go subtracts foreground rectangles from visible image regions, bounds the number of placement slices, and skips unchanged placements. | Keep transient details out of the five shell slots. Preserve uncovered frame segments, restore covered segments on close, and emit graphics only when geometry changes. Add open-popup resize and differing-client tests before claiming support. |

TUIOS manages PTYs, terminal emulation and composition itself. Porting that stack would change this project's architecture. Our frame can use a bounded alpha mask for one native popup without introducing another multiplexer or terminal emulator. The current popup mask records one client's opening rectangle; resizing an open popup and multiple clients remain acceptance work. Do not present this as the full TUIOS compositor.

Sources: [Workmux popup documentation](https://github.com/raine/workmux/blob/3cef212252896a9d69d01cc946a95d6cbf25978f/docs/src/content/docs/guide/dashboard/index.mdx), [popup renderer](https://github.com/raine/workmux/blob/3cef212252896a9d69d01cc946a95d6cbf25978f/src/command/dashboard/ui/popup.rs), [tmux identity handling](https://github.com/raine/workmux/blob/3cef212252896a9d69d01cc946a95d6cbf25978f/src/multiplexer/tmux.rs), [TUIOS popup geometry](https://github.com/Gaurav-Gosain/tuios/blob/42084d968e7d2db2438abe4aa1378a3de35954ca/internal/app/os_popup.go), [Kitty occlusion](https://github.com/Gaurav-Gosain/tuios/blob/42084d968e7d2db2438abe4aa1378a3de35954ca/internal/app/kitty_occlusion.go), [popup tests](https://github.com/Gaurav-Gosain/tuios/blob/42084d968e7d2db2438abe4aa1378a3de35954ca/internal/app/popup_test.go).

## 3. Integrate borders without spending a sixth of the shell area

The full-layout experiment reuses the shell-tab image as its relative-placement anchor, the existing separator columns for its sides, and one empty padding row below the shell. It adds no frame worker. The tab renderer includes geometry in its existing snapshot and uploads a new frame only on layout, client or popup changes. Keep this opt-in through launch.py --install-shell-frame while resize, recovery and multi-client checks continue.

The standalone border probe proves the contour and input separation. Its two-cell bands and native separators consumed 14.76% of the reviewed viewport. Do not copy that allocation into the full layout without reducing it. Reuse the existing shell tab/header region as an anchor where possible, and measure the smallest safe gutters across font sizes.

Keep the one-query snapshot while integration remains a prototype. Consider a persistent tmux control connection or event notifications only after measurements justify the extra lifecycle code. Preserve stable graphics IDs and metadata-only heartbeats.

Read [the border experiment](BORDER-EXPERIMENT.md) for commands, evidence, and outstanding multi-client checks. Popup and background experiments must share the same explicit ownership and cleanup rules for images.

## Implementation order

1. Compare the static dotted background with the upstream CSS and choose the renderer layer.
2. Open one functional process-details popup using native tmux features. Prove focus and cleanup before artwork.
3. Reduce border gutters and integrate the frame with the existing shell header. Review popup occlusion as part of that work.
4. Add file search and text preview through existing Yazi/editor tools. Test image/PDF support as a separate milestone.

Keep AUR packaging first in the distribution plan. Mise remains planning only. Retest Ubuntu later; do not expand this visual pass into a system-theme rewrite or a mobile-client compatibility claim.

### Current checkpoint (2026-10-25)

- The [visual audit](VISUAL-AUDIT.md) records source comparisons and terminal-specific adaptations. IPv4 now receives the upstream half-row allocation; process percentages have separate right-aligned bounds. Smaller instrument fonts prevent metadata collisions in short columns. The resize handler now fixes the uneven side columns and compressed tab strip exposed at 160x40. We inspected shrink/restore in Omarchy and tested 140x40 through 240x60 on both distros. Actual client resizing and a second font scale still need review.
- Three ten-second local performance samples measured 133.80% to 145.99% of one CPU core across the selected process groups. The network-column raster path costs more CPU than the system column in the separate microbenchmarks. Profile that path before changing the animation rate or adding caches. Long stability checks, frame-pacing measurements and a release budget remain open; see [validation](VALIDATION.md).
- The [FPS comparisons](PERFORMANCE.md) tested 24/30/48/60 before optimization, then repeated in reverse order after optimization. At a 30 target, the optimized workers submitted 29.28 FPS for System and 28.66 for Network in the VM. Use 30 as the next opt-in candidate for longer stability and native-hardware checks; keep the default at 24. The higher targets still fell short, and submission rate does not prove displayed FPS.
- The raster pass now projects visible globe tiles, reuses converted polygon inks with a public Pillow fallback, and caches repeated text measurements. Pixel comparisons and both full distro suites passed. Shuffled CPU microbenchmarks reduced median network render-and-encode time from 28.223 to 18.775 ms and system time from 13.910 to 9.632 ms. The post-change 24 FPS live trial measured 93.59% of one CPU core across selected process groups; avoid treating separate shared-host trials as a portable savings percentage.

- Keep the native top popup. The custom process-table renderer and its graphics transport experiment have been removed. Its opening-rectangle frame mask remains a limitation when dragging or resizing; do not describe that as solved.
- Share the pinned primary color and CSS alpha blends across instruments, Yazi and the dedicated terminal palette. Memory uses 10%, 30% and full primary ink for free, available and active points. Continue checking typography, ratios and remaining state fills against upstream.
- Ubuntu's tmux 3.4 needs LF config files. The repository already specifies LF in .gitattributes; Windows copy workflows must preserve those bytes.
- Profile the selected server, its descendants, attached tmux clients and their Kitty ancestor. Report shared-page RSS and unobserved short-lived processes as limits. Controlled Electron comparisons remain deferred.
- Frame recovery now waits for the tab anchor bootstrap, refreshes its relative placement after parent heartbeats, and replaces its owned root on geometry or popup-mask changes. We inspected restart, reattach and native top closure. Keep multi-client work open.
- Use the opt-in local temporary-file transport for the VM and WSLg reviews. Direct multipart transfers produced Kitty decompression/zero-dimension errors during reattach; stabilize that path before claiming SSH support. Keep local-file mode off across SSH. It uses Kitty's protocol rather than another renderer process.

### Owner's next milestone sequence (2026-10-25)

Checkpoint: we inspected actual Kitty window resizing and a second font scale in Omarchy, then restored the normal window without replacing its native shell. The ten-minute 30/24 FPS run completed without worker death. Ubuntu's live workers now include the larger keyboard and aligned arrows; its earlier source copy had not reloaded those processes. We also added an offline check for 31 bundled artifact hashes. See validation and performance for measurements and limits.

Before the first local alpha, run a clean-checkout launch/stop check, review the package contents and public screenshots, and prepare the Arch/AUR packaging. Review the experiment for merging before tagging a release. Native popup movement/resize occlusion, direct-transfer reattach, multiple clients and physical touch remain limitations; do not claim those paths work in the first release. Keep 24 FPS as the default. Longer runs and native-hardware measurements can inform a later default change.

The clean-source and package checkpoint is complete in the prepared Omarchy VM: source export launch/stop, Arch recipe build, archive inspection, installed-command visual review and package removal. We fixed the keyboard's slow-first-frame reveal and stopped outside controls from resetting the server's graphics transport. Both full distro suites pass. Next, test a clean Arch build and package upgrade, review release contents and the experiment diff, and settle popup limitations before merging or tagging. The preview recipe follows this branch; no AUR package or release has been published.

The 2026-10-26 clean Arch build and installed upgrade passed. We corrected the preview license path and checked all 20 staged runtime imports. The clean build passed its 23 checks; package integrity and the 31 asset hashes passed after upgrade. We inspected the restarted interface and removed the test package while preserving the original review session and checked configs. Next is the [final alpha review](RELEASE-CHECKLIST.md): inspect the experiment diff and release contents, state the supported local workflow and popup limits, then review merging and tagging. Keep the film-boardroom branch and mobile transport work after that milestone.

1. Finish popup open, drag, interaction and close behavior against the security-patched eDEX Modal, modal.css and TopList implementations. Use native terminal controls where they preserve the behavior. Check mouse/touch event routing, focus restoration, clipping during movement, resize, cancellation and child exit. Reproduce only animations present upstream; its custom modal closes with a 100 ms blink.
2. Audit UI and terminal colors, opacity, shapes, typography and layout ratios against the pinned upstream. Record terminal-cell and hardware constraints, and explain adaptations rather than claiming pixel equivalence. Keep functional labels and existing shell/file-browser behavior.
3. Run performance checks and validate the current interface on the disposable Ubuntu test distro as well as Omarchy. Include renderer workers, descendants, tmux and Kitty in end-to-end measurements. Keep upstream comparisons controlled, and state display/GPU limitations.
4. Update usage, compatibility and validation documentation after the implementations pass. Then prune and organize the codebase and prepare the first release, with Arch/AUR packaging first. Do not publish a release before these gates pass.
5. Start a separate branch for the closer film-boardroom layout and palette, using the existing framework. Keep the eDEX reconstruction available.
6. Investigate mobile SSH responsiveness and graphics support with measured network conditions. Aim to minimize input and rendering delay; do not promise zero latency. Establish client capability and Mosh compatibility before recommending a setup.
7. Improve Yazi/shell workflows: explicit file opening or editing in a chosen shell, copying file and directory paths, quoting paths, clipboard availability over SSH, and preserving the browser and shell directories unless an action explicitly changes them. Test with spaces, Unicode and shell metacharacters.

The owner has now authorized the Ubuntu compatibility and performance pass after popup and visual work. The older deferral below records the initial order; it does not block that milestone.

## Deferred: compare performance against upstream in WSL

Use disposable distro containers inside WSL for repeatable Arch and Debian dependency setups. Plan a comparison with the pinned Electron upstream after the background, edges and popup work settles. Do not start this benchmark as part of the current visual pass.

Match viewport size, visible modules, keyboard visibility, sample workload and animation rate. Measure idle and active CPU, resident memory, startup time, frame pacing and graphics traffic. Include Kitty, tmux, instrument workers and the compositor or display bridge in the port's totals; include Electron's renderer and helper processes in upstream's totals. Record GPU versus software rendering and WSLg/container display overhead. Run warm-up and repeated samples, and report the environment limits alongside results. Containers share the WSL kernel and display path, so these numbers will not establish native Omarchy performance. Keep claims of a performance advantage out of the README until measurements support them.

## Deferred: a closer film-boardroom interpretation

Treat eDEX-UI as an author's interpretation of the TRON boardroom interface. Reconstructing eDEX does not establish fidelity to the film. Finish the current eDEX background, edge and popup work before starting a separate visual direction.

For that later goal, inspect [Rob Scanlon's arscan/encom-boardroom](https://github.com/arscan/encom-boardroom) alongside film stills and [GMUNK's boardroom project](https://work.gmunk.com/TRON-Board-Room), which Scanlon links in his README. Compare palette, typography, panel proportions, globe/network forms, motion and border details. Record which elements come from a film reference, which come from arscan's implementation, and which we adapt to terminal constraints. Scanlon's README distinguishes his globe focus from his looser adaptations of other film elements, so use scene references to settle discrepancies.

Build a reference sheet and prototype selected elements in a separate branch or opt-in preset. Keep the finished eDEX preset available. Reuse existing metrics, native shells and tmux panes; do not add a browser runtime or a second terminal emulator for the styling. Keep functional labels. Review asset and font licenses before copying anything. The owner's existing encom-boardroom fork has its own repository and should remain separate from this TUI project's history.
