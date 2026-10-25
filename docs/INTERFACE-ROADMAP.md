# Interface roadmap

Research snapshot: 2026-10-25. These are plans, not installed features. Keep the normal layout on main until each experiment passes visual and interaction checks.

## 1. Restore the upstream dotted background

The pinned eDEX main.css defines two crossed linear gradients over the theme's grey. Each dark band occupies 1.85vh of a 2.04vh period. Their intersections leave small square dots. The tron theme uses #05080d for light_black and #262828 for grey. At a 1080px viewport, the period is about 22px and the dots are about 2px wide. Centering and fractional pixel coverage affect the exact phase and edge pixels.

The upstream renderer toggles the solidBackground class during its title sequence and clears it before the main UI. Our boot.py draws a simplified point grid during parts of startup; our steady-state Kitty config has background_image none. The persistent background is still missing. Do not replace it with a circuit-board illustration or an animated particle field.

Start with a static tile generated from those CSS dimensions and colors. Test Kitty's native tiled background in a project-specific configuration. Generate the tile for the reviewed viewport, and compare it against a browser-rendered CSS reference. Regenerate on viewport changes only if the comparison shows a material difference. A static background needs no frame loop or metric collector.

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

## 3. Integrate borders without spending a sixth of the shell area

The standalone border probe proves the contour and input separation. Its two-cell bands and native separators consumed 14.76% of the reviewed viewport. Do not copy that allocation into the full layout without reducing it. Reuse the existing shell tab/header region as an anchor where possible, and measure the smallest safe gutters across font sizes.

Keep the one-query snapshot while integration remains a prototype. Consider a persistent tmux control connection or event notifications only after measurements justify the extra lifecycle code. Preserve stable graphics IDs and metadata-only heartbeats.

Read [the border experiment](BORDER-EXPERIMENT.md) for commands, evidence, and outstanding multi-client checks. Popup and background experiments must share the same explicit ownership and cleanup rules for images.

## Implementation order

1. Compare the static dotted background with the upstream CSS and choose the renderer layer.
2. Open one functional process-details popup using native tmux features. Prove focus and cleanup before artwork.
3. Reduce border gutters and integrate the frame with the existing shell header. Review popup occlusion as part of that work.
4. Add file search and text preview through existing Yazi/editor tools. Test image/PDF support as a separate milestone.

Keep AUR packaging first in the distribution plan. Mise remains planning only. Retest Ubuntu later; do not expand this visual pass into a system-theme rewrite or a mobile-client compatibility claim.
