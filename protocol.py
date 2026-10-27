"""Kitty graphics transport with tmux passthrough and cell-anchored placement.

GPL-3.0. Implements the published Kitty protocol; no terminal emulator inside tmux.
"""
import base64
import os
from pathlib import Path
import secrets
import contextlib
import tempfile


def flipped_payload(payload, size, channels):
    """Compensate for a client's inverted image origin without moving cells."""
    import zlib
    if size is not None:
        width,height=size;stride=width*channels
        pixels=zlib.decompress(payload)
        if width<=0 or height<=0 or len(pixels)!=stride*height:
            raise ValueError('invalid raw image dimensions for orientation correction')
        flipped=b''.join(pixels[y*stride:(y+1)*stride] for y in range(height-1,-1,-1))
        return zlib.compress(flipped,1)
    import io
    from PIL import Image as Raster
    with Raster.open(io.BytesIO(payload)) as original:
        flipped=original.transpose(Raster.Transpose.FLIP_TOP_BOTTOM)
        output=io.BytesIO();flipped.save(output,format='PNG',compress_level=2)
        return output.getvalue()


@contextlib.contextmanager
def graphics_lock(stream):
    # Kitty chunk assembly is terminal-global. Independent tmux pane writers
    # must not interleave their multipart graphics commands.
    if not os.environ.get('TMUX') or not stream.isatty():
        yield
        return
    import fcntl
    path=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp')) / f'edex-terminal-{os.getuid()}.graphics.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        if os.fstat(fd).st_uid!=os.getuid():raise PermissionError('Graphics lock is owned by another user')
        fcntl.flock(fd,fcntl.LOCK_EX)
        try:yield
        finally:
            stream.flush();fcntl.flock(fd,fcntl.LOCK_UN)
    finally:os.close(fd)

ESC = b'\x1b'
DIACRITICS = [chr(int(line.split(';')[0], 16)) for line in
              (Path(__file__).parent / 'assets/rowcolumn-diacritics.txt').read_text().splitlines()
              if line and not line.startswith('#')]


def command(params, payload=b'', tmux=None):
    packet = ESC + b'_G' + ','.join(f'{k}={v}' for k, v in params.items()).encode()
    packet += (b';' + payload if payload else b'') + ESC + b'\\'
    if tmux if tmux is not None else bool(os.environ.get('TMUX')):
        packet = ESC + b'Ptmux;' + packet.replace(ESC, ESC + ESC) + ESC + b'\\'
    return packet


class Image:
    def __init__(self, stream, image_id=None, tmux=None):
        self.stream = stream
        self.id = image_id or secrets.randbelow(0xFFFFFE) + 1
        self.tmux = tmux
        self.loaded = False
        self.placement_id = 1
        self.pending_files=set()

    def send(self, **params):
        with graphics_lock(self.stream):
            self.stream.write(command(dict(i=self.id, q=2, **params), tmux=self.tmux))

    def pixels(self, png, update=False, *, size=None, channels=3):
        # Base64 chunks are bounded for tmux's passthrough parser. Updating the
        # existing root frame bounds image/frame storage instead of appending.
        if channels not in (3,4):raise ValueError('raw graphics require RGB or RGBA')
        if os.environ.get('EDEX_GRAPHICS_FLIP_Y')=='1':
            png=flipped_payload(png,size,channels)
        if os.environ.get('EDEX_GRAPHICS_TRANSPORT')=='tempfile':
            self.pending_files={path for path in self.pending_files if path.exists()}
            if len(self.pending_files)>=128:raise RuntimeError('Kitty local image transfer backlog exceeded 128 files')
            fd,path=tempfile.mkstemp(prefix='tty-graphics-protocol-edex-')
            path=Path(path);self.pending_files.add(path)
            try:
                with os.fdopen(fd,'wb') as output:output.write(png)
                params=dict(a='f' if update and self.loaded else 't',t='t',
                            f=channels*8 if size else 100,i=self.id,q=2)
                if size:params.update(s=size[0],v=size[1],o='z')
                if update and self.loaded:params.update(r=1,X=1)
                with graphics_lock(self.stream):
                    self.stream.write(command(params,base64.b64encode(os.fsencode(path)),self.tmux))
            except BaseException:
                path.unlink(missing_ok=True);self.pending_files.discard(path);raise
            self.loaded=True
            return
        encoded = base64.b64encode(png)
        chunks = [encoded[i:i+2048] for i in range(0, len(encoded), 2048)]
        with graphics_lock(self.stream):
            for index, chunk in enumerate(chunks):
                params = dict(m=int(index < len(chunks)-1))
                # The protocol allows only m/q on continuation packets, plus
                # a=f for animation data. Image/frame metadata belongs to the
                # first packet; repeating it can restart a partial transfer.
                if update and self.loaded:params.update(a='f',q=2)
                if index == 0:
                    params.update(a='f' if update and self.loaded else 't', f=channels*8 if size else 100, i=self.id, q=2)
                    if size:params.update(s=size[0],v=size[1],o='z')
                    if update and self.loaded:
                        params.update(r=1, X=1)
                self.stream.write(command(params, chunk, self.tmux))
        self.loaded = True

    def place(self, columns, rows, *, repaint=True):
        columns = max(1, min(columns, len(DIACRITICS)))
        rows = max(1, min(rows, len(DIACRITICS)))
        self.send(a='p', U=1, p=self.placement_id, c=columns, r=rows)
        if not repaint:return
        color = (f'\x1b[38;2;{self.id >> 16};{(self.id >> 8) & 255};{self.id & 255}m'
                 f'\x1b[58;2;0;0;{self.placement_id}m')
        # These are normal tmux cells, not absolute terminal coordinates.
        cells=[]
        for row in range(rows):
            line = ''.join('\U0010eeee' + DIACRITICS[row] + DIACRITICS[col] for col in range(columns))
            cells.append((f'\x1b[{row+1};1H' + color + line + '\x1b[0m').encode())
        # tmux understands synchronized output: commit cell repaint as a unit.
        self.stream.write(b'\x1b[?2026h'+b''.join(cells)+b'\x1b[?2026l')
        self.stream.flush()

    def close(self):
        self.send(a='d', d='I')  # Only this pane's random image id, never delete-all.
        self.stream.flush()
        for path in self.pending_files:path.unlink(missing_ok=True)
        self.pending_files.clear()
