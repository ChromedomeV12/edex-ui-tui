# Agent handoff

Updated 2026-10-24. Read this file before choosing a development task. Check Git status and the owner's latest instructions; this snapshot does not establish that a VM or test session still runs.

## Project and direction

We reconstruct eDEX-UI in a Linux terminal with Kitty graphics and tmux panes. The owner wants the upstream interface, animation, and interaction details. A TRON recolor alone does not meet that goal. Use the security-patched fork pinned in UPSTREAM.json as the reference. Preserve the original eDEX name and credits.

Keep the central shell native. Reuse existing tools where they fit; Yazi handles file operations. Keep labels useful: system data and actions should retain their functional names. The owner rejected decorative fictional subsystem headings and an extra desktop or Electron layer.

This repository covers the terminal reconstruction. The broader TRON customizations and Omarchy system theme belong to other projects.

## Branches and checkouts

| Branch | Purpose |
| --- | --- |
| main | Reviewed working baseline, public docs, and CI |
| experiment/kitty-borders | Border research in a separate Git worktree |

The border branch contains a research plan in docs/BORDER-EXPERIMENT.md. We have not implemented the graphical border prototype. Native tmux borders remain active. Use a separate session for experiments, and preserve the owner's working VM session. Recheck worktree paths with `git worktree list`; do not assume the owner's filesystem layout.

## Accepted behavior

- Five shell tabs preserve their processes and working directories. Empty slots start on demand. Ctrl-b then 1–5 switches tabs.
- The keyboard starts hidden. Ctrl-b then Shift-K toggles it. It sends input to the selected central shell, with one-shot sticky modifiers and latched Caps/Fn.
- In Yazi, arrows move through the grid, Enter opens the highlighted item, and Backspace goes up. Clicking highlights a card. The browser keeps its own directory. Read docs/FILE-NAVIGATION.md for batch actions and shortcuts.
- System and network panes use real Linux counters. Do not invent geographic endpoints or substitute illustrative values without labeling them.
- Renderers target 24 FPS with compressed RGB transfers. Keep graphics IDs stable and serialize multipart writes. Metadata-only heartbeats fixed observed blanking; periodic cell rewrites or image-ID rotation can reintroduce flicker.
- Use OFL Rajdhani by default. Users may supply licensed United Sans files. Do not distribute commercial fonts or claim that we established the exact movie typeface.

## Validation and environment

Current interface work targets a disposable Omarchy VM. The reviewed setup uses Kitty 0.49.2, tmux 3.8, Yazi 26.9.1, Python 3.14, and Pillow 12.3. Read docs/VALIDATION.md for bounded measurements and limitations. The extracted source passed the Linux suite on that VM. CI passed on Python 3.11 and 3.13 after adding Kitty terminfo to the runner.

Run `python3 tests/run.py` from the root on a Linux machine with the documented dependencies. The tests create private tmux servers and temporary fixtures. CI runs the Python and Lua contracts; it does not install Yazi or run the real Yazi navigation integration check. Run that check in the reviewed environment.

Check actual rendered images after visual changes. A live process does not prove visible graphics. Preserve shell state, zoom/restore behavior, mouse input, and keyboard toggling. Run input tests against a recorder, not a live shell. Never log typed content.

The owner deferred the current Ubuntu pass. Do not change the physical Omarchy machine, normal shell/tmux/Yazi configuration, VM graphics settings, or the parked system theme as part of this project. The working VM installation predates repository extraction and still uses the old file layout. Test a separate copy; copying a new tree over that installation can break its launch paths.

Private connection details belong in an ignored local/AGENT-ENVIRONMENT.md supplied by the owner. Fresh clones do not include access credentials or deployment state. Ask for missing access rather than guessing hosts or reinstalling systems.

## Remaining work

The next candidate is the clipped shell border. Kitty relative placements may anchor a transparent frame to a placeholder parent, with drawing confined to reserved gutters. Test resize, zoom, reattach, hidden anchors, mouse selection, multiple clients, flicker, and idle cost before merging. This is a documented proposal, not a verified implementation.

Physical typing does not animate the on-screen keyboard. Synthetic mouse taps pass the isolated tests; real tablet touch, long-press repeat, and simultaneous touches remain unverified or unfinished. Tablet SSH clients need the relevant graphics and mouse support. We have not established Mosh compatibility. Read docs/KEYBOARD.md before input work.

We still have gaps in startup choreography, audio, upstream effects, and typography. Do not describe the current port as pixel-perfect. Compare against reference frames and report discrepancies.

## Distribution decisions

The owner prefers AUR packaging first for Arch/Omarchy. Mise remains a planning option for development and release tasks; do not implement it without resuming that work. We have no application package metadata, AUR package, or tagged release yet. Dependency setup commands in the README describe the current source checkout.

## Leave the next agent a useful snapshot

After a task, update the relevant guide and this handoff if behavior or priorities changed. Record the branch, checks, observed failures, and what remains untested. Keep host paths, credentials, raw shell input, and private captures out of public docs. Scan staged files before publishing. Follow CONTRIBUTING.md and SECURITY.md; retain upstream and font notices.
