# Keyboard fidelity and input testing

## Current layout

The port now uses measured bounds from the pinned upstream keyboard.css and en-US keymap at a 1920x1080 reference viewport. Geometry is uniformly fitted to the pane, preserving key proportions, staggered rows and the overlapping two-part Enter. Previously the port omitted CSS border widths and independently compressed the rows. Primary/secondary font sizes and their positions now follow the CSS snapshots for normal, Shift and Fn states. DELETE is hidden until Shift is active. The four original SVG arrow icons are retained, including their translucent frames.

Rajdhani SemiBold is the open-licensed default for these heading-weight labels. United Sans remains an optional locally supplied font, not bundled. Layout fidelity does not establish pixel-identical typography to the movie or commercial font. assets/keyboard-geometry.json records the browser-measured reference; UPSTREAM.json records derivation and source hashes. Raster output uses supersampling for fractional borders. No browser runs in the live port.

Show/hide with Ctrl-b then Shift-K. Tap a key to type into the selected shell slot. Shift, Ctrl and Alt are sticky for one subsequent key; Caps and Fn remain latched until toggled. This supports single-touch clients without requiring simultaneous modifier touches. Holding a key for upstream-style auto-repeat and true multi-touch are not implemented.

## What the original does with a physical keyboard

The pinned [keyboard.class.js](https://github.com/theelderemo/eDEX-UI-security-patched/blob/d59e5e287d9ebde8920aaf638ae7e685115c3de4/src/classes/keyboard.class.js) explicitly binds document.onkeydown and document.onkeyup to the displayed keyboard. Keydown highlights the matching key, including both Enter elements; keyup applies a brief blink and clears it after 100ms. Modifier state changes the legends. Window blur clears stuck highlights. It also handles touchstart, touchend and touchcancel and supports delayed repeat while held.

The terminal port currently animates on-screen key taps, but does NOT mirror physical typing from the central shell onto this keyboard. Reading bytes in the keyboard pane cannot observe input delivered to another tmux pane. This difference remains explicit rather than using a global keyboard listener.

A future bridge should be limited to this isolated tmux session and enabled only while the keyboard is shown. It should observe key identities without persisting typed text, preserve the original input path and avoid fork-per-key helpers. Ordinary terminal bytes do not carry modifier-only down/up events; exact held-key/release mirroring would require compatible [Kitty keyboard protocol event reporting](https://sw.kovidgoyal.net/kitty/keyboard-protocol/) through the actual client and tmux, or an explicitly scoped client bridge. No such bridge or global hook was installed in this pass.

## Automated tap-path check

Run from the repository root on Linux:

```sh
python3 tests/test_keyboard_touch.py
```

This starts a temporary isolated tmux server and real tmux client on a PTY. Synthetic SGR press/release events enter the CLIENT side, so tmux must select the pane and translate mouse coordinates before the keyboard sees them. The target is a raw-byte recorder, never a shell. The test verifies letters, sticky Shift, Space, Back, Enter, all arrows, Ctrl-C, and that a right-click injects nothing. It tears down its own processes and temporary files.

This proves the mouse-emulated tap route under the tested tmux version. It does not prove that a physical touchscreen or particular tablet SSH app generates these events.

## Real touchscreen acceptance check

1. Use a client with Kitty graphics/Unicode placeholders and SGR mouse support. Enable its touch-to-left-click/mouse mode if needed; terminal scroll/selection gestures are not necessarily clicks. The tablet/client combination has not yet been validated.
2. Show the keyboard with Ctrl-b then Shift-K and select the intended shell tab.
3. In that central shell, run `python3 keyboard_input_probe.py`. The probe displays received byte representations without executing or saving them.
4. Tap a few letter keys at their centers and near their edges. Check that each tap produces one byte for the intended key. Tap Shift then a: expect `b'A'`. Tap Back: expect `b'\x08'`; Enter: `b'\r'`; Up: `b'\x1bOA'`. The probe may show several bytes together when input is batched.
5. Check that releasing or cancelling a touch causes no extra character or stuck highlight. Test after resizing and switching between shell slots. The selected slot owns the input target, so start a probe in each slot before testing it.
6. Tap Ctrl then d, or use physical Ctrl-D, to exit the probe and restore normal terminal mode.

A client which shows the graphics but scrolls/selects text on tap has not passed the input check. True simultaneous multi-touch and long-press repeat are separate remaining capabilities.
