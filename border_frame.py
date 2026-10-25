#!/usr/bin/env python3
"""Clipped shell frame renderer for the border probe (border_probe.py).

Runs in the probe's full-width 2-row header pane as
`border_frame.py --shell-pane <shell-pane-id>`. The pane's first cell is the
window top-left: a 1x1 anchor image (opaque project background, which hides
the placeholder glyph on the flat #05080d header) anchors a full-window
frame placed relatively (a=p, H=0, V=0, c=window_cols, r=window_rows), so
the frame follows resizes without moving the cursor or touching the shell
pane.

render_frame(width, height, shell_box) -> RGBA (Pillow): width x height are
window pixels; shell_box (left, top, right, bottom) is the shell pane's
exclusive pixel bounds; every shell pixel is (0,0,0,0). The frame is one
closed contour ring: square top-left/bottom-right corners, clipped
top-right/bottom-left corners. The ring is the outer polygon minus the
inner polygon ported from the pinned upstream reference (see
_ring_polygons); stroke, gutter growth and the per-corner cut clamping
follow the constants and comments in this file. Rasterized with 4x box
coverage, including the upstream parent's outer clip over its border layer.
Color: render.py CYAN #aacfd1 at 50% opacity (straight
color, partial alpha only on anti-aliased edges).
Corner geometry adapted from augmented-ui 1.1.2, Copyright (c) James0x57,
PropJockey, 2019; BSD-2-Clause, see NOTICE.md and UPSTREAM.json. The pinned
upstream package-lock names augmented-ui 2.0.0, but its markup is
incompatible with the old ui.html; the 1.1.2 legacy sheet is the one the
markup matches (verified by rendering the upstream CSS in Chromium).

Invariants:
  - This process owns exactly two kitty image IDs (anchor, frame), stable
    for the process lifetime. Plain geometry changes re-upload the frame as
    a=t under the same ID (PNG payload without size=; size= is for zlib
    raw-RGB uploads) and refresh the relative placement metadata; no
    periodic repaints, no animation loop.
  - First attach, reattach, client change and unzoom are recoveries: the
    same owned IDs are re-uploaded as a=t with an anchor cell repaint
    (kitty graphics state is per client; this is what prevents stale
    frames).
  - Detach, shell zoom or hidden window: the frame is marked not present
    and the anchor cell blanked, so the frame cannot outlive its anchor;
    the owned IDs are kept, a later visible recovery re-uploads them in
    place, and the client image store never accumulates frames.
  - tmux is polled in one snapshot through the inherited TMUX environment
    (probe server), never by session name, at 0.5s cadence; a failed
    query keeps the last confirmed state instead of redrawing.
  - A single attached client is the supported limit (a second client sees
    a scaled frame); no mouse hooks, no input routing; all writes go
    through protocol.graphics_lock and never reach the shell pane.
  - On signal or exit the owned images are deleted only while the frame is
    visible, when the write can reach kitty; a hidden parent window hides
    the frame by itself, and stored images are left to kitty's next
    visible or terminal-wide cleanup. If the renderer process exits, its
    pane dies with it and the frame is gone; border_probe.py does not
    respawn it — rebuild the probe session.

GPL-3.0. Port of the eDEX main_shell clipped contour; see UPSTREAM.json.
"""
import argparse
import io
import os
import signal
import sys
import time

from PIL import Image as PILImage
from PIL import ImageChops
from PIL import ImageDraw

from protocol import Image
from tmux_control import query

STROKE = (170, 207, 209)         # render.py CYAN #aacfd1, straight color
STROKE_ALPHA = 128               # 50% opacity, --aug-border-opacity
ANCHOR_PIXEL = (5, 8, 13, 255)   # project background #05080d, hides the glyph
STROKE_RATIO = 0.0018            # 0.18vh of the window pixel height
PADDING_RATIO = 0.0074           # 0.74vh of the window pixel height
CLIP = 15.0                      # augmented-ui 1.1.2 --aug-tr/--aug-bl clip size
POLL = 0.5                       # seconds between modest geometry polls


def _coverage(width, height, outer, inner):
    """Box-sampled border coverage multiplied by the parent's outer clip."""
    ss = 4
    mask = PILImage.new('L', (width * ss, height * ss), 0)
    draw = ImageDraw.Draw(mask)
    scale = lambda points: [(x * ss + 0.5, y * ss + 0.5) for x, y in points]
    draw.polygon(scale(outer), fill=255)
    outer_mask = mask.resize((width, height), PILImage.Resampling.BOX)
    draw.polygon(scale(inner), fill=0)
    border_mask = mask.resize((width, height), PILImage.Resampling.BOX)
    return ImageChops.multiply(outer_mask, border_mask)


def _ring_polygons(L, T, R, B, s, clip_tr, clip_bl):
    """Outer/inner ring polygons in window pixels (augmented-ui 1.1.2
    tr-clip/bl-clip geometry): square TL/BR corners, 45-degree normal cuts
    of `clip_tr`/`clip_bl` at TR/BL; inner offset by stroke s with the
    miter join clip + s/2 on the cut corners."""
    outer = [(L, T), (R - clip_tr, T), (R, T + clip_tr),
             (R, B), (L + clip_bl, B), (L, B - clip_bl)]
    inner = [(L + s, T + s), (R - clip_tr - s / 2, T + s), (R - s, T + clip_tr + s / 2),
             (R - s, B - s), (L + clip_bl + s / 2, B - s), (L + s, B - clip_bl - s / 2)]
    return outer, inner


def render_frame(width, height, shell_box):
    """Render the clipped frame for a width x height px window.

    shell_box is the shell pane's exclusive pixel bounds; every pixel
    inside it is fully transparent. The ring bbox hugs the probe gutters
    around the shell box; the TR/BL cuts use the source 15px clip, clamped
    per corner so a tiny gutter cannot cut through the shell corner and
    break the contour.
    """
    width, height = int(width), int(height)
    image = PILImage.new('RGBA', (max(0, width), max(0, height)), (0, 0, 0, 0))
    if width < 1 or height < 1:
        return image
    left = max(0, int(shell_box[0]))
    top = max(0, int(shell_box[1]))
    right = min(width, int(shell_box[2]))
    bottom = min(height, int(shell_box[3]))
    if right <= left or bottom <= top:
        return image
    s = STROKE_RATIO * height
    padding = int(height * PADDING_RATIO + 0.5)
    # Per-side bbox extent: padding + stroke, clamped to the gutter so the
    # shell area always keeps its clearance.
    extent = padding + s
    L = left - min(extent, left)
    T = top - min(extent, top)
    R = right + min(extent, width - right)
    B = bottom + min(extent, height - bottom)
    gutters = (left - L, top - T, R - right, B - bottom)
    if not any(gutters):
        return image  # no gutter room: the frame would sit inside the shell
    # A side whose gutter is smaller than the stroke drops the stroke to
    # that gutter, so the ring never intrudes on the shell area.
    s = min(s, min(g for g in gutters if g))
    if R - L < s or B - T < s:
        return image  # ring bbox too small to hold a stroke
    # Per-corner cut: the source 15px when it fits, otherwise clamped so
    # the inner diagonal (x - y <= R - T - clip - 1.5 s at TR) stays short
    # of the shell corner and the ring stays connected around it.
    room = min(CLIP, R - L - 1.5 * s, B - T - 1.5 * s)
    clip_tr = max(0.0, min(room, (top - T) + (R - right) - 1.5 * s))
    clip_bl = max(0.0, min(room, (B - bottom) + (left - L) - 1.5 * s))
    coverage = _coverage(width, height, *_ring_polygons(L, T, R, B, s, clip_tr, clip_bl))
    alpha = coverage.point(lambda v: (v * STROKE_ALPHA + 127) // 255)
    on = alpha.point(lambda a: 255 if a else 0)
    channels = [ImageChops.multiply(PILImage.new('L', (width, height), value), on)
                for value in STROKE]
    image = PILImage.merge('RGBA', (*channels, alpha))
    # Shell pixels are always transparent, even when clamping pushed the
    # ring bbox against the shell edge.
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, top, right - 1, bottom - 1), fill=(0, 0, 0, 0))
    return image


def _frame_png(cols, rows, cell, left, top, pw, ph):
    width, height = cols * cell[0], rows * cell[1]
    shell_box = (left * cell[0], top * cell[1],
                 (left + pw) * cell[0], (top + ph) * cell[1])
    buffer = io.BytesIO()
    # PNG payload: protocol.Image.pixels sends it without size (size= is for
    # zlib raw-RGB uploads and would mis-decode this image).
    render_frame(width, height, shell_box).save(buffer, format='PNG', compress_level=2)
    return buffer.getvalue()


def _anchor_png():
    buffer = io.BytesIO()
    PILImage.new('RGBA', (1, 1), ANCHOR_PIXEL).save(buffer, format='PNG', compress_level=2)
    return buffer.getvalue()


SNAPSHOT_FORMAT = (
    '#{session_attached},#{window_active},#{window_zoomed_flag},'
    '#{client_cell_width},#{client_cell_height},#{client_pid},#{client_created};'
    '#{window_width},#{window_height},#{pane_left},#{pane_top},#{pane_width},#{pane_height};'
    '#{P:#{pane_id}|#{@edex-border-side}|#{pane_width}|#{pane_height}|#{pane_active}~}'
)


def _poll(shell_pane):
    """Read client, shell, and gutter state in one tmux process."""
    snapshot = query('display-message', '-p', '-t', shell_pane, SNAPSHOT_FORMAT)
    if snapshot is None:
        return None
    try:
        state, geometry, raw_panes = snapshot.split(';')
        attached, active, zoomed, cw, ch = map(int, state.split(',')[:5])
        client = tuple(state.split(',')[5:])
        cols, rows, left, top, pw, ph = map(int, geometry.split(','))
        panes = []
        selected = False
        for raw in raw_panes.rstrip('~').split('~'):
            pane, side, width, height, pane_active = raw.split('|')
            panes.append((pane, side, int(width), int(height)))
            if pane == os.environ.get('TMUX_PANE'):
                selected = pane_active == '1'
    except (ValueError, TypeError):
        return None
    visible = attached > 0 and active and (not zoomed or selected) and cw > 0 and ch > 0
    return visible, (cols, rows, (cw, ch), left, top, pw, ph), client, panes


def _fit_gutters(panes):
    """Restore reserved bands after tmux distributes a client resize."""
    changed = False
    for pane, side, width, height in panes:
        if side not in ('top', 'bottom', 'left', 'right'):
            continue
        vertical = side in ('top', 'bottom')
        if (height if vertical else width) != 2:
            if query('resize-pane', '-t', pane, '-y' if vertical else '-x', '2') is None:
                return changed
            changed = True
    return changed


def _place_frame(frame, anchor, cols, rows):
    # Relative placement from our stable window-top-left anchor; the cursor
    # never moves and no cells are written for a relative placement.
    frame.send(a='p', p=frame.placement_id, P=anchor.id, Q=anchor.placement_id,
               H=0, V=0, c=cols, r=rows)


def run(stream, shell_pane):
    alive = True
    winch = False

    def stop(*_):
        nonlocal alive
        alive = False

    def on_winch(*_):
        nonlocal winch
        winch = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGWINCH, on_winch)

    # Stable for the process lifetime: recovery re-uploads these same
    # owned IDs in place instead of minting new ones, so the client image
    # store never accumulates frames.
    anchor = Image(stream)
    frame = Image(stream)
    present = False
    signature = None
    client_signature = None

    def hide():
        # Mark the frame not present and blank the anchor cell; the owned
        # image IDs are kept so a later visible recovery re-uploads them
        # in place. A dropped write (hidden window) is fine: the parent
        # window hides the frame either way.
        nonlocal present, signature
        if not present:
            return
        present = False
        signature = None
        try:
            # Blank the anchor cell so the placeholder glyph is never the
            # visible residue of a hidden frame.
            stream.write(b'\x1b[1;1H\x1b[0m ')
            stream.flush()
        except Exception:
            pass

    def show(geometry):
        # Visible recovery (first attach, reattach, client change, unzoom,
        # or a hidden period): re-upload the same owned IDs (a=t, no
        # size), repaint the anchor cell, re-place the frame relatively.
        nonlocal present, signature
        cols, rows, cell, left, top, pw, ph = geometry
        anchor.pixels(_anchor_png())
        anchor.place(1, 1)
        frame.pixels(_frame_png(cols, rows, cell, left, top, pw, ph))
        _place_frame(frame, anchor, cols, rows)
        stream.flush()
        present = True
        signature = geometry

    def refresh(geometry):
        # Plain geometry change: same frame ID re-uploaded as a=t (image
        # data replaced in place) and the relative placement refreshed; the
        # anchor is never touched.
        nonlocal signature
        cols, rows, cell, left, top, pw, ph = geometry
        frame.pixels(_frame_png(cols, rows, cell, left, top, pw, ph))
        _place_frame(frame, anchor, cols, rows)
        stream.flush()
        signature = geometry

    try:
        stream.write(b'\x1b[?25l')
        stream.flush()
        while alive:
            if not winch:
                time.sleep(POLL)
            winch = False
            probe = _poll(shell_pane)
            if probe is None:
                time.sleep(0.1)
                continue
            visible, geometry, clients, panes = probe
            if not visible:
                if present:
                    hide()
                continue
            if min(geometry[:2]) >= 8 and _fit_gutters(panes):
                probe = _poll(shell_pane)
                if probe is None or not probe[0]:
                    continue
                visible, geometry, clients, panes = probe
            if clients != client_signature or not present:
                # First attach, reattach, client change or a hidden period:
                # kitty's graphics state is per client, so a stale frame is
                # impossible only after the owned IDs are re-uploaded for
                # this client.
                client_signature = clients
                show(geometry)
            elif geometry != signature:
                refresh(geometry)
    finally:
        # Delete the owned images only while the frame is visible, when the
        # write can reach kitty; a hidden parent window hides the frame by
        # itself and the stored images are left to kitty's next visible or
        # terminal-wide cleanup.
        if present:
            for image in (frame, anchor):
                try:
                    image.close()
                except Exception:
                    pass
        try:
            stream.write(b'\x1b[?25h')
            stream.flush()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--shell-pane', required=True,
                        help='tmux pane id of the native shell (frame target)')
    args = parser.parse_args()
    if not os.environ.get('TMUX'):
        parser.error('must run inside a tmux pane on the probe server')
    if not os.environ.get('TMUX_PANE'):
        parser.error('TMUX_PANE is required to locate the anchor cell')
    if not sys.stdout.isatty():
        parser.error('a Kitty terminal pane is required')
    stream = sys.stdout.buffer
    run(stream, args.shell_pane)


if __name__ == '__main__':
    main()
