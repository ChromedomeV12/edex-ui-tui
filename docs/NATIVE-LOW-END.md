# Native older-laptop checkpoint

On 2026-10-27 we measured the published Arch alpha on native Omarchy 4.0.6: Intel Core i7-4850HQ, four cores/eight logical CPUs, about 16 GiB RAM and a Nouveau graphics driver. Packages: Kitty 0.49.2, tmux 3.8, Python 3.14.8 and Pillow 13.0.0. The client had 155 columns by 42 rows, the optional shell frame enabled and the keyboard hidden.

Raw process records stay private because pane titles contain user/host identifiers. This record includes aggregate measurements and hardware class. We changed no fan controller, power governor, graphics driver or global terminal configuration.

## Live samples

CPU scope includes the selected tmux server, attached client, descendants and Kitty ancestor. One logical core equals 100%. Summed RSS double-counts shared pages. Compositor/GPU work falls outside these totals.

| Target | Sample | Session descendants | Kitty | Total app CPU, one core | Summed RSS |
| --- | --- | --- | --- | --- | --- |
| 24 FPS | 30 seconds | 93.33% | 22.93% | 117.76% | 420.70 MiB |
| 8 FPS | 20 seconds | 35.86% | 9.19% | 46.10% | 424.09 MiB |

At 24 FPS, the system/network workers used 43.50%/49.37% of one core; file navigation used 0.13%. The lower-rate trial used about 61% less process CPU with fewer animation updates. This is a short rate comparison, not a saving at equal visual quality. We preserved the native shell PID while replacing only instrument workers. Detached renderers paused and used little CPU in a separate counter sample.

During the longer 24 FPS checkpoint, the CPU sensor read 99°C, GPU 69–70°C and fans about 6,156/5,700 RPM, their reported limits. A later 8 FPS sample read 94°C CPU, 76°C GPU and about 3,854/3,571 RPM. We did not control ambient temperature, other workloads, cooling condition or thermal steady state. These readings neither isolate the app as the sole heat source nor establish a thermal fix.

## CPU microbenchmarks

After the live 24 FPS sample, the profiler rendered/encoded 24 frames using one sampled data set. Canvas sizes differ from the live panes. Timings exclude Kitty, tmux, network transfer and display scanout.

| Instrument / canvas | PNG median / p95 | Zlib RGB median / p95 | Mean RGB payload |
| --- | --- | --- | --- |
| System, 396×640 | 10.007 / 10.810 ms | 5.621 / 6.433 ms | 30,590 bytes |
| Network, 360×640 | 16.815 / 18.093 ms | 12.420 / 13.139 ms | 37,842 bytes |

The collector's 12-sample CPU median was 22.681 ms, p95 27.663 ms. Both instrument workers collect once per second. Shared collection could save some work, but rendering and presentation account for more of the measured cost.

## Next prerelease priorities

1. Cache static instrument surfaces/text apart from moving plots and the globe. Rebuild on resize or relevant data changes. Verify pixel equivalence and label freshness before comparing CPU.
2. Measure dirty-rectangle root-frame updates at equal target and geometry. Preserve stable image IDs, clipping and serialized writes. Compare payload bytes, Kitty CPU and remote bandwidth.
3. Keep 8/12 as opt-in targets and 24 as default pending more native data. Record submitted intervals and p95 work time. Do not raise the default from VM-only results.
4. Reproduce the globe flash on native Kitty and a compatible SSH client, using a fixed raster sequence and recording resize/placement/root-reset events. Neither lower FPS nor a protocol correction proves a visual fix.
5. Repeat idle, typing/navigation, keyboard-show and resize scenarios after each change. Include warm-up and thermal trends, note background workloads and preserve shell PIDs. Measure startup apart from steady-state rendering.

The fixes live on fix/launch-routing. We did not replace published artifacts or installed runtime files. The lower-rate worker arguments belong to the running test session; a new launch of the installed alpha retains its original default.
