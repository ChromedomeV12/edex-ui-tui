# System surface cache review

Review date: 2026-10-27. Patch: 77776fac211f32b03822ee7c53ba78e92a4a7981, based on 76a3cc4. We reviewed the four-file patch and tested a combined tree with the current launch/layout branch through 7b521f9. The combine reported no conflicts. We did not merge or deploy the patch.

## Result

We found no blocking runtime defect in this review. The worker retains one static system surface and one metrics snapshot. Metrics.sample returns a new dictionary each time; the cache relies on that contract. Size, RGB/RGBA mode, snapshot identity and clock-second changes rebuild it. Startup and oversized canvases use the reference renderer. Callers receive a copy, so drawing motion does not corrupt the retained surface. The image limit is 8 MiB, excluding the output frame and retained metrics.

The network path, collection rate, 24 FPS default, graphics IDs and transport remain unchanged. The motion helper duplicates the reference graph geometry; keep pixel-equivalence checks when changing that layout.

## Independent checks

The combined source passed the full Ubuntu runtime/Lua suite, including the newer 120×40 bottom-panel and orientation tests. Cached/reference image checks passed in RGB and RGBA, across startup, invalidation, resize and caller mutation. We also inspected a live 130×42 WSLg window after the cache entered its steady path, with the optional keyboard and frame. Clock, memory grid, curves and labels appeared in the expected positions. The private capture contains host details and stays outside Git.

We reran the supplied matched harness in a separate review directory, preserving the agent's results. It used Python 3.12.3, Pillow 10.2, five shuffled trials per case and 24 frames per trial, including two cache rebuilds. We checked pixel equality on each measured frame.

| Canvas / mode | Baseline → cached mean CPU time | Reduction |
| --- | --- | --- |
| 225×560 RGB | 3.979 → 2.420 ms | 39.2% |
| 225×560 RGBA | 4.408 → 2.564 ms | 41.8% |
| 306×600 RGB | 4.870 → 3.280 ms | 32.6% |
| 306×600 RGBA | 4.987 → 3.578 ms | 28.3% |

The new sequence supports the direction of the agent's 28.7–39.2% result. It does not establish a portable percentage. Compressed payload bytes stayed identical. The measurements exclude Kitty, tmux, compositor, network and presentation costs; we have no new native whole-app, fan or thermal result.

## Follow-ups before a performance release

- Commit a portable matched benchmark harness or an exact reproduction command. The reviewed harness and raw records remain private development artifacts.
- Label the existing profiler's raster results as the uncached reference, or add a cached comparison. Its live process measurements still cover the running application, but its raster microbenchmark does not exercise ColumnRenderer.
- Repeat the native older-laptop workflow before making whole-app claims. Include the actual SSH client and any image-orientation correction, which adds its own decode/re-encode work. Keep the network/globe hotspot and thermal conditions in view.

These follow-ups do not require a broader renderer rewrite. Keep the cache patch separate until the next performance phase; the current iPad orientation fix does not deploy it.
