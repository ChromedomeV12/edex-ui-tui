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

The separate CPU profile points to globe projection and thousands of per-frame polygon calls as the largest network-column costs. System rendering spends time measuring text as well as encoding. In the live trials, median upload calls stayed below one millisecond while the network raster/encode median ranged from 30.44 to 37.32 ms. Optimize and validate the rendering path before trading more CPU for a higher target. These observations do not establish a universal bottleneck for other terminals, sizes or SSH transport.
