# Performance checks

The default animation target is 24 FPS. The launcher accepts 24, 30, 48 and 60 for new sessions through `--fps`. An existing session keeps its current workers when you reattach. The target controls instrument animation; Linux counters still sample once per second, and the optional keyboard redraws for input and reveal states.

## System surface cache, 2026-10-27

The performance branch caches one completed system-column surface per worker.
It redraws moving CPU curves over a copy, and rebuilds the surface when the
metrics snapshot, wall-clock second, canvas size or RGB/RGBA mode changes.
Startup fades use the original path. The default remains 24 FPS. Network/globe
rendering stays on its original path: trial caching there did not produce a
reliable CPU saving.

The cache retains one image, capped at 8 MiB, plus its current metrics snapshot.
Oversized canvases bypass and release it. At the measured sizes the retained
image uses 0.36–0.70 MiB, in addition to the current output frame. This changes
neither graphics IDs nor placement/transport behavior. Compressed payload bytes
remain identical, so this change makes no bandwidth-saving claim.

We compared source commit 76a3cc4 with the cached path on Ubuntu 24.04 WSL,
Python 3.12.3 and Pillow 10.2.0. Each case used five shuffled baseline/candidate
trials of 24 frames, the same eight-CPU synthetic data and zlib level 1.
The system cache rebuilt twice per trial: once for the metrics snapshot and
once for an offset wall-clock tick. We verified the pixels against the baseline
for every measured frame. The table shows the median of trial means, including
both rebuilds, and median trial p95 work time.

| Canvas / mode | Baseline mean / p95, ms | Cached mean / p95, ms | CPU-time reduction |
| --- | --- | --- | --- |
| 225×560 RGB | 3.489 / 4.101 | 2.166 / 3.345 | 37.9% |
| 225×560 RGBA | 3.890 / 4.750 | 2.367 / 3.793 | 39.2% |
| 306×600 RGB | 3.904 / 4.736 | 2.783 / 4.217 | 28.7% |
| 306×600 RGBA | 4.586 / 6.165 | 3.186 / 4.392 | 30.5% |

These are render-and-encode CPU microbenchmarks. They exclude Kitty, tmux,
compositor/GPU work, network transfer and display presentation. We have not
measured a whole-app CPU, RSS, fan or thermal improvement on native hardware
after this change. Keep the [older-laptop checkpoint](NATIVE-LOW-END.md) as the
native baseline and repeat that workflow before making those claims.
The existing profile_panes.py raster microbenchmark still calls the uncached
reference renderer; this cache comparison uses a separate matched harness.

Regression checks compare cached and uncached pixels across startup, clock/data
changes, RGB/RGBA and sizes down to 180×140. They cover resize invalidation,
single-entry memory bounds, the oversized bypass and caller mutation of returned
frames. The full Ubuntu runtime/Lua suite passed. Tests also passed with Pillow
12.3.0 on Windows. Raw trials and diagnostic captures stay outside Git.

A new live WSLg capture remains pending. The isolated review window failed to
start in this session; its logs reported missing D-Bus machine identity and a
graphics-driver initialization failure. An app-scoped X11/software fallback did
not produce a review window. We changed no distro settings to repair that
environment. Inspect the interface on a working graphical test setup before
merging or claiming live visual verification of this change.

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

### Five-minute phases at 30 and 24

We followed the short trial with two consecutive five-minute phases in the same Omarchy review. Each phase used an eight-second warm-up and 15-second process snapshots. We restarted only the instrument workers between targets and restored uninstrumented 24 FPS workers afterward. The native shell survived both transitions.

| Target | Duration, seconds | System submitted FPS | Network submitted FPS | CPU, percent of one core | Summed RSS first / last / peak, MiB |
| --- | --- | --- | --- | --- | --- |
| 30 | 301.19 | 29.30 | 28.71 | 112.81 | 561.49 / 566.53 / 566.53 |
| 24 | 301.17 | 23.73 | 23.47 | 96.86 | 561.90 / 565.50 / 565.50 |

The selected pane PIDs stayed unchanged within each phase. The sampled shared graphics temporary-file pool peaked at six files in each phase; that pool includes other project images in the VM and does not isolate each worker. RSS includes shared pages more than once. CPU excludes compositor/GPU work, and the host also ran WSLg. These observations support keeping 30 available as an opt-in target. Keep 24 as the default pending native-hardware checks and longer runs. Submission rates do not measure displayed frame pacing.
