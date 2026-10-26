"""Build a local Ubuntu alpha with dpkg-deb; no root or user-config changes."""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime, parseaddr
import gzip
import hashlib
import importlib.util
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('edex_staging', ROOT / 'packaging/install.py')
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


def copyright_text():
    notice = (ROOT / 'NOTICE.md').read_text(encoding='utf-8')
    bsd = notice.split('```text\n', 1)[1].split('```', 1)[0].strip()
    ofl = (ROOT / 'assets/fonts/OFL.txt').read_text(encoding='utf-8').strip()
    def block(value):
        return '\n'.join(' ' + (line if line else '.') for line in value.splitlines())
    return ("Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n"
            "Upstream-Name: eDEX-UI TUI\nSource: https://github.com/ChromedomeV12/edex-ui-tui\n\n"
            "Files: *\nCopyright: eDEX-UI TUI contributors\n"
            " 2017-2021 Gabriel 'Squared' SAILLARD and eDEX-UI contributors\nLicense: GPL-3\n\n"
            "Files: assets/fonts/*\nCopyright: 2014 Indian Type Foundry (info@indiantypefoundry.com)\nLicense: OFL-1.1\n\n"
            "Files: border_frame.py shell_edges.py\nCopyright: eDEX-UI TUI contributors\n"
            " 2019 James0x57, PropJockey\nLicense: GPL-3 and BSD-2-clause\n\n"
            "License: GPL-3\n On Debian systems, the complete GNU GPL version 3 is in\n"
            " /usr/share/common-licenses/GPL-3.\n\nLicense: BSD-2-clause\n" + block(bsd) +
            '\n\nLicense: OFL-1.1\n' + block(ofl) + '\n')


def build(output, maintainer, version='0.1.0~alpha1-1', epoch=None):
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+:~\-]*', version):
        raise ValueError('invalid Debian version')
    name, address = parseaddr(maintainer)
    if not name or not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', address) or any(c in maintainer for c in '\r\n'):
        raise ValueError('provide a single maintainer name and public email')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output / f'edex-ui-tui_{version}_all.deb'
    if package.exists():
        raise FileExistsError(f'output already exists: {package.name}')
    default_epoch = int(Path(__file__).stat().st_mtime)
    epoch = int(epoch if epoch is not None else os.environ.get('SOURCE_DATE_EPOCH', str(default_epoch)))
    with tempfile.TemporaryDirectory(prefix='edex-deb-', dir=output) as folder:
        dest = Path(folder)
        staging.stage(dest, interpreter='/usr/bin/python3')
        docs = dest / 'usr/share/doc/edex-ui-tui'
        # These are files created in this private staging root, never host paths.
        licenses = dest / 'usr/share/licenses/edex-ui-tui'
        target = docs / 'licenses'
        licenses.rename(target)
        licenses.parent.rmdir()
        (docs / 'copyright').write_text(copyright_text(), encoding='utf-8', newline='\n')
        changelog = (f'edex-ui-tui ({version}) unstable; urgency=low\n\n'
                     '  * Prepare the local Ubuntu alpha with the shared runtime and assets.\n\n'
                     f' -- {maintainer}  {format_datetime(datetime.fromtimestamp(epoch, timezone.utc))}\n')
        (docs / 'changelog.Debian.gz').write_bytes(gzip.compress(changelog.encode(), mtime=epoch))
        man = dest / 'usr/share/man/man1'
        man.mkdir(parents=True)
        (man / 'edex-ui-tui.1.gz').write_bytes(gzip.compress(
            (ROOT / 'packaging/debian/edex-ui-tui.1').read_bytes(), mtime=epoch))
        data_files = sorted(p for p in dest.rglob('*') if p.is_file())
        installed_size = sum(math.ceil(p.stat().st_size / 1024) for p in data_files)
        control = dest / 'DEBIAN'
        control.mkdir()
        text = (f'Package: edex-ui-tui\nVersion: {version}\nArchitecture: all\n'
                f'Maintainer: {maintainer}\nSection: utils\nPriority: optional\nInstalled-Size: {installed_size}\n'
                'Depends: python3 (>= 3.11), python3-pil (>= 10.2), kitty (>= 0.32.2), tmux (>= 3.4), fonts-dejavu-core, procps\n'
                'Recommends: librsvg2-bin\nSuggests: yazi (>= 26.9.1)\n'
                'Homepage: https://github.com/ChromedomeV12/edex-ui-tui\n'
                'Description: terminal workspace inspired by eDEX-UI\n'
                ' Native tmux shells, live Linux instruments, Kitty graphics and an optional\n'
                ' on-screen keyboard. This alpha targets one local Kitty client.\n')
        (control / 'control').write_text(text, encoding='utf-8', newline='\n')
        (control / 'md5sums').write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest() + '  ' +
                                      p.relative_to(dest).as_posix() + '\n' for p in data_files), encoding='utf-8', newline='\n')
        for path in sorted(dest.rglob('*'), reverse=True):
            path.chmod(0o755 if path.is_dir() or path == dest/'usr/bin/edex-ui-tui' else 0o644)
            os.utime(path, (epoch, epoch))
        dest.chmod(0o755)
        os.utime(dest, (epoch, epoch))
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(dest), str(package)],
                       check=True, env=dict(os.environ, SOURCE_DATE_EPOCH=str(epoch)))
    return package


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    contact = parser.add_mutually_exclusive_group(required=True)
    contact.add_argument('--maintainer')
    contact.add_argument('--maintainer-file', type=Path)
    parser.add_argument('--version', default='0.1.0~alpha1-1')
    parser.add_argument('--epoch', type=int)
    args = parser.parse_args()
    maintainer = args.maintainer if args.maintainer is not None else args.maintainer_file.read_text(encoding='utf-8').strip()
    print(build(args.output, maintainer, args.version, args.epoch))
