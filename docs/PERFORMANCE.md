# Performance checks

The default animation target is 24 FPS. The launcher accepts 24, 30, 48 and 60 for new sessions through `--fps`. An existing session keeps its current workers when you reattach. The target controls instrument animation; Linux counters still sample once per second, and the optional keyboard redraws for input and reveal states.

## Compare targets

Use the same Kitty version, font size, viewport, visible panes and graphics transport for each trial. Keep a native shell idle and leave Yazi on the same directory. Warm up after launch, then take repeated samples. Test targets in more than one order before claiming an improvement.

From another terminal, select the same project socket and run:

```sh
python3 profile_panes.py --seconds 10 --frames 12
```

The profiler counts the selected tmux server, descendants, attached clients and their Kitty ancestor. It also runs separate CPU render-and-encode microbenchmarks after the live sample. Those microbenchmarks do not measure display FPS. Read the accounting limits in the JSON output and [validation record](VALIDATION.md).

For developer trials, each instrument can write to its own `EDEX_METRIC_LOG` path. Use separate private paths per worker. The report includes the target, frame count, elapsed time, raster/upload timing and submission intervals. The metric calls a frame submitted after the write and flush complete; it cannot confirm Kitty presentation or monitor scanout. Compare frame-count deltas over the reports' elapsed-time deltas after warm-up. Reports update every five seconds and on graceful worker exit.

## Decision gates

Keep 24 as the baseline until measurements and live observation support a higher default. Check interval tails and interaction responsiveness as well as average submission rate. A target that saturates one instrument worker can increase jitter despite a higher average. A workload that meets 60 FPS on one desktop may not do so in a VM, WSLg, over SSH, or at a different font scale.

We have not established an advantage over Electron. We defer that controlled comparison to its roadmap milestone. Mobile SSH/Mosh, multiple clients and physical touch remain separate compatibility work.

## First target comparison, 2026-10-25

We tested one ascending sequence in the disposable Omarchy VM with Kitty 0.49.2, tmux 3.8 and local temporary-file graphics. The layout stayed at 209x49 cells with the keyboard visible. For each target, we restarted only the two instrument workers, warmed them for eight seconds, then sampled the selected process groups for ten seconds. We calculated steady submission rates from successive worker reports after warm-up. The native shell PID stayed unchanged; we restored both instruments to 24 FPS afterward.

| Target FPS | System submitted FPS | Network submitted FPS | CPU, percent of one core |
| --- | --- | --- | --- |
| 24 | 23.44 | 21.75 | 139.92 |
| 30 | 28.45 | 23.54 | 151.68 |
| 48 | 38.94 | 27.40 | 193.52 |
| 60 | 42.60 | 22.81 | 188.63 |

Keep 24 as the default. The VM did not sustain either higher target in both instruments; 60 did not improve the network pane in this sequence. One ascending sequence cannot separate target effects from host scheduling and thermal variation, and these are submission rates rather than display measurements. Repeat in another order and on native hardware after optimization before recommending a higher default. The opt-in targets allow that testing.

The separate CPU profile pointed to globe projection and thousands of per-frame polygon calls as the largest network-column costs. System rendering spent time measuring text as well as encoding. In the live trials, median upload calls stayed below one millisecond while the network raster/encode median ranged from 30.44 to 37.32 ms. We used those measurements to choose the following optimizations. These observations do not establish a universal bottleneck for other terminals, sizes or SSH transport.

## Raster optimization, 2026-10-25

The optimized globe projects visible tiles after the depth check. The source mesh has almost no shared vertices, so the previous full-sphere deduplication saved little work and allocated points for hidden tiles. We retain the projection arithmetic, face order, shading and Pillow polygon primitive.

Pillow's public polygon wrapper converts its outline color on each call. We cache those converted inks for RGB and RGBA and call the same polygon primitive. This fast path uses Pillow internals, so we retain the public ImageDraw.polygon fallback when the conversion interface or primitive signature is unavailable. The raster tests compare both paths with the previous renderer and exercise an incompatible primitive signature. Run them when updating Pillow.

Text measurement uses a bounded 2,048-entry cache; fitted strings use a bounded 1,024-entry cache. Those caches avoid measuring the same labels and truncation candidates on successive frames. They retain the existing font metrics and ellipsis rules.

We compared the previous implementation, the optimized implementation and its public fallback using the same synthetic instrument data, a transparent 306x600 canvas, and zlib level 1. Each of five repetitions shuffled the implementation order, warmed four frames and measured 24 frames with process CPU time. The table shows the median of each repetition's median render-and-encode time.

| Instrument | Previous, ms | Optimized, ms | Public fallback, ms |
| --- | --- | --- | --- |
| System | 13.910 | 9.632 | 10.332 |
| Network | 28.223 | 18.775 | 26.474 |

These CPU microbenchmarks exclude Kitty and use synthetic long metadata with stable values. They measure rendering and encoding costs, including cache reuse, rather than end-to-end savings or display FPS. The small difference between the two system paths reflects trial variance; the system instrument does not draw the globe. We added no rendering dependency.

### Post-optimization live trial

We repeated the VM trial with the optimized workers in reverse order: 60, 48, 30, then 24. The layout, warm-up and measurement periods matched the first trial. The table lists targets in ascending order for comparison.

| Target FPS | System submitted FPS | Network submitted FPS | CPU, percent of one core |
| --- | --- | --- | --- |
| 24 | 23.86 | 23.48 | 93.59 |
| 30 | 29.28 | 28.66 | 116.17 |
| 48 | 43.65 | 37.24 | 164.80 |
| 60 | 51.75 | 40.99 | 188.76 |

At the 24 target, the new trial used 93.59% of one core versus 139.92% in the earlier trial and submitted closer to the requested rate. The shuffled CPU microbenchmarks support a rendering improvement, but the two live sequences happened at different times on a shared host. Treat the totals as VM observations rather than a portable percentage-saving claim.

Use 30 as the next opt-in candidate for longer stability and native-hardware tests. Both instruments approached that target, while 48 and 60 still fell short. Keep 24 as the release baseline until those further checks support changing it. We restored the review workers to 24, kept the native shell PID and inspected the interface afterward. These trials still do not measure Kitty presentation or monitor scanout.
