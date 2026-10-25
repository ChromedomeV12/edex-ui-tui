# Contributing

You can help with rendering, input, accessibility, performance, or Linux compatibility. Open an issue with a reproduction or send a focused pull request. Tell us if you used AI assistance, and review the code and test results you submit.

## Project layout

| Path | Purpose |
| --- | --- |
| launch.py, tmux.conf, kitty.conf | Isolated session and terminal setup |
| panel.py, columns.py, render.py, metrics.py | Instruments, drawing, Linux counters |
| protocol.py, tmux_control.py | Graphics transport and tmux queries |
| shell_tabs.py, workspaces.py | Tab drawing and native shell slots |
| layout.py | Resize-only reflow of existing panes |
| keyboard.py, keyboard_input_probe.py | Optional keyboard and manual input probe |
| navigator.py, file_icons.py, navigation/ | File browser integration and Yazi grid |
| assets/ | Runtime data, SVG icon data, and OFL fonts |
| references/ | Pinned upstream source for comparison; no runtime JavaScript |
| tests/ | Unit, geometry, and isolated integration checks |
| docs/ | User guides, measurements, and validation limits |
| app.py, packaging/ | Local window entry point and Arch preview staging |

We keep runtime modules at the root so the launcher and pane subprocesses share one import and asset path. Use Python 3.11 or newer, Pillow, tmux, Lua, Yazi, and librsvg for the full test suite. Follow the README for the reviewed versions.

## Test changes

Give one contributor ownership of each runtime path during a change. Agree on interfaces before splitting launcher and renderer work, and write the final usage guide after the interface settles. Run focused tests while editing, then the full suite at the integration checkpoint. Keep agent session exports and private captures outside the source tree.

Run from the repository root on Linux:

```sh
python3 tests/run.py
```

The runner executes the Python checks and Lua grid assertions. Integration checks create private tmux servers and temporary fixtures. Install the dependencies before running; a missing dependency counts as a failure. The tests do not type commands into your live shells. Run `python3 tests/test_port.py` for the portable subset; Windows skips Linux-only contracts. GitHub Actions runs the Python and Lua contracts on Python 3.11 and 3.13; run the real Yazi integration check on a machine with the reviewed Yazi version.

For visual changes, launch a separate session and inspect startup, steady motion, resizing, pane zoom, keyboard toggling, and shell switching. Test reattach too. Report what you checked and what remains untested. Process liveness alone does not prove that Kitty displays the graphics. Use `python3 profile_panes.py` to measure the selected session's process groups and render cost. Read its accounting limits before comparing totals. Preserve LF endings when copying configs from Windows; tmux 3.4 rejects CRLF option values.

## Keep the working baseline

Branch from main. Work on border experiments in `experiment/kitty-borders` and a separate checkout. Keep the default layout until screenshots and interaction tests support a change. Do not test against a live user's shell or the physical Omarchy machine without authorization.

Run border experiments from a separate guest checkout in a separate desktop Kitty window outside tmux. Set `EDEX_TMUX_SOCKET` to a unique name for the launcher, controls, and profiler. Unset or empty selects the baseline socket, `edex-terminal-<uid>`; there is no inference from `TMUX`. Newly launched server children inherit the selector, but existing shells keep their spawn-time environment. Supply the variable on commands from outside the experiment or from older shells. Workspace locks are socket-scoped; graphics serialization stays global per uid. See docs/BORDER-EXPERIMENT.md for commands and teardown.

Preserve native shell behavior and the optional keyboard. Keep graphics placement IDs stable across heartbeats, serialize multipart transfers, and repaint placeholder cells for initialization or recovery. Use functional labels and real metrics. Document missing data rather than inventing endpoints or locations.

## Submit a change

Explain the user-visible problem, your change, and the checks you ran. Include sanitized before/after images for layout changes. Remove hostnames, IP addresses, personal paths, file listings, and shell history from evidence. Keep capture logs, virtual environments, private fonts, and credentials out of Git.

Retain upstream notices and record new copied assets in UPSTREAM.json with their origin and hashes. Do not submit commercial fonts. By submitting a contribution, you agree to distribute your contribution under this project's GPL-3.0 terms, subject to existing third-party notices. We do not require a separate contributor agreement.

In UPSTREAM.json, sha256 identifies the bundled file's bytes with repository-enforced line endings. Use source_sha256 for the original pinned upstream Git blob when extracting a subset or changing content, and describe the adaptation. Read that blob with git show, rather than hashing an upstream Windows checkout that may contain converted line endings. The provenance test checks declared bundled hashes offline; verifying new source hashes still requires the pinned upstream content. Test an archive or fresh checkout before publishing hash changes.
