# Visual audit

Review date: 2026-10-25. We compare the experiment with the security-patched upstream revision in [UPSTREAM.json](../UPSTREAM.json). We retain the owner's larger keyboard and solid terminal inset where those choices differ from upstream.

## Source comparison

| Element | Reference | Current result and limits |
| --- | --- | --- |
| Primary ink and dark surface | [tron.json](../references/tron.json) | Shared #aacfd1 ink and #05080d surface. CSS alpha states use opaque blends over that surface; the dotted background changes the effective backdrop beneath transparent artwork. |
| Rules, muted text and memory states | [CPU CSS](../references/css/mod_cpuinfo.css), [memory CSS](../references/css/mod_ramwatcher.css) | Rules use 30% primary; muted text uses 50%. Memory distinguishes 10%, 30% and full primary. |
| Network status row | [netstat CSS](../references/css/mod_netstat.css) | State and Ping each take one quarter of the row; IPv4 takes the middle half. The previous equal-width columns truncated addresses. No external ping or location lookup runs. |
| Process table | [toplist CSS](../references/css/mod_toplist.css) | Bounded PID/name columns and right-aligned CPU/memory values. Long names use an ellipsis. The port adapts widths to its font metrics rather than copying fixed browser vw values. |
| Instrument text | [system info CSS](../references/css/mod_sysinfo.css), [column CSS](../references/css/mod_column.css) | Font sizes follow column height. Lower font-size floors prevent short-column collisions. This remains an adaptation of browser vh sizing. |
| Fonts | [theme font declarations](../references/tron.json) | Upstream requests United Sans Medium/Light and Fira Mono. We bundle OFL Rajdhani and accept owner-supplied licensed display fonts. We do not claim matching glyph outlines or browser letter spacing. |
| Shell tabs | [shell CSS](../references/css/main_shell.css) | Five slots, upstream-derived height and 35-degree slant. Native shell input remains in tmux. |
| Main frame | [shell CSS](../references/css/main_shell.css) | Clipped upper-right/lower-left corners and square opposite corners. The owner requested a solid inset. Native popup movement can exceed the frame's opening-rectangle mask. |
| Keyboard | [keyboard CSS](../references/css/keyboard.css) | Uniform measured layout, overlapping Enter, original arrow SVGs and shifted legends. The owner requested a larger pane and centered Up/Down alignment. Physical-key mirroring, held-key repeat and multi-touch remain incomplete. |
| File browser | Pinned filesystem icons and isolated Yazi grid | Upstream icons over shared dots. Native terminal glyph metrics and cell-based selection differ from the browser. |

## Size and interaction checks

We inspected instrument renders at 350x680, 260x500 and 220x420 pixels with synthetic long process names, seven-digit PIDs, 1600.0% CPU, 100.0% memory and a full-length IPv4 address. The rendering test checks actual glyph bounds for CPU/memory separation and uptime label/value spacing; it also checks that the full address reaches the renderer at those sizes. We retain the source data and truncate only the displayed string when space runs out.

We inspected the live Omarchy review at 209x49 terminal cells, with the keyboard visible, then reduced the same tmux window to 160x40 and restored it. The shell PID remained unchanged and the instruments kept rendering. This changes tmux's logical window inside the existing Kitty client; it does not simulate a resized desktop or establish high-DPI behavior.

The first smaller-window check exposed uneven tmux reflow: side columns narrowed disproportionately and the tab pane fell to one row. The resize handler now restores both columns to 17% of the window width, the visible keyboard to 62%, and the lower strip to 36% height with the keyboard or 30% without it. It derives the tab pane's height from the artwork and cell height, and retains one frame-padding row. The existing tab worker triggers this work on window/cell-size changes; it adds no polling process and does not replace shells. We inspected the corrected 160x40 layout and its return to 209x49 in Omarchy.

The private tmux tests cover 140x40, 160x40, 209x49 and 240x60, hidden keyboard space, zoom preservation and unchanged pane PIDs. A second pass at the same size performs no resize mutations. Keyboard toggling and workspace changes share the same socket-scoped lock with reflow. These checks do not establish faithful proportions at arbitrary window sizes or high-DPI behavior. A native process popup still uses the accepted rectangular viewer and has limited frame occlusion during movement.

## Remaining release checks

- We inspected actual 1600x950 and restored 1896x1007 Kitty windows, plus 13-point text at 10x23 cell pixels and restored 11-point text at 9x20. The frame and visible panes fit, and the native shell survived. Selection and keyboard interaction at the second font scale remain open.
- We inspected Ubuntu's refreshed live workers: its keyboard grew from 100x15 to 111x18 cells with aligned Up/Down keys. Earlier source/tests alone had not refreshed those workers.
- The ten-minute local run completed at 30 and 24 FPS targets without worker death. Native-hardware performance and longer stability remain open; see [performance](PERFORMANCE.md).
- Keep SSH/direct-transfer, multiple-client and physical-touch claims outside the first local alpha until their separate checks pass.
