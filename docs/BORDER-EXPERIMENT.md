# Kitty border experiment

## Baseline

Main retains the reviewed tmux layout. Use this branch in a separate worktree for border experiments. Do not replace the running VM session or change normal terminal configuration.

## Candidate

Kitty documents [relative image placements](https://sw.kovidgoyal.net/kitty/graphics-protocol/#relative-placements) that can follow a Unicode-placeholder parent. Test a frame anchored to the existing tab header, with transparent pixels over the shell and drawing confined to reserved gutters. Follow the upstream main_shell.css bottom-left and top-right clipped contours.

Keep native shell input, selection, and tmux mouse behavior. Update the frame on layout changes; static borders need no animation loop. Check whether a process-free empty tmux pane can reserve the required space before adding another renderer process.

## Checks before merging

- Compare a reference frame with the prototype at the same viewport and cell size. Measure the gutter cost.
- Resize, zoom, switch shell tabs, show and hide the keyboard, detach, and reattach. Check hidden anchors and stale images.
- Test mouse selection, pane resizing, and shell text near the corners. Decorations must not cover text or consume input.
- Sample static regions for flicker using stable image and placement IDs. Measure idle CPU and transport volume.
- Test two clients with different dimensions, or document a supported single-client limit with evidence.
- Run the existing tests. Show captures and record failures before proposing a default change.

We have not implemented or tested the relative-placement frame yet. Native tmux borders remain active on this branch until a prototype passes these checks.
