# Ubuntu alpha preparation

Use experiment/ubuntu-alpha for the first Ubuntu binary package. We started this branch from the prepared Arch experiment and kept its runtime, keyboard geometry, clipped frame and assets. Main retains the earlier baseline. The Arch alpha bundle remains frozen; this work does not replace its source archive or checksum.

## Supported local test

We tested Ubuntu 24.04 Noble in a disposable WSL2 distro with WSLg, Python 3.12.3, Pillow 10.2.0, Kitty 0.32.2 and tmux 3.4. The optional icon grid used Yazi 26.9.1. This does not establish support for other Debian releases, native Ubuntu graphics drivers, mobile clients or Mosh.

The package depends on python3, python3-pil, kitty, tmux, fonts-dejavu-core and procps. It recommends librsvg2-bin. Noble does not supply the reviewed Yazi version in its standard archive; install Yazi 26.9.1 or newer from a source you trust if you want the icon grid. Without Yazi, the automatic file mode can use the bundled preview. We do not download Yazi in an installation script.

## Build

Install the build and runtime dependencies in a disposable Ubuntu environment:

```sh
sudo apt install python3 python3-pil kitty tmux fonts-dejavu-core procps librsvg2-bin dpkg-dev
```

From this branch's checkout, supply the package maintainer's public name and email in a private text file. Use a public contact intended for the release; do not commit that file.

```sh
python3 packaging/debian/build.py --output "$HOME/edex-packages" \
  --maintainer-file "$HOME/edex-maintainer.txt" --epoch 1792972800
dpkg-deb --info "$HOME/edex-packages/edex-ui-tui_0.1.0~alpha1-1_all.deb"
dpkg-deb --contents "$HOME/edex-packages/edex-ui-tui_0.1.0~alpha1-1_all.deb"
```

The builder needs no root privileges. Use the same source, maintainer field, version and epoch for reproducible bytes. It refuses to overwrite an existing package. Version 0.1.0~alpha1-1 sorts before 0.1.0. Architecture all covers the Python/data payload; dependencies still need binaries for your machine.

We use dpkg-deb to prepare a local binary package. We have not prepared a Debian source package, PPA, signed APT repository or distribution submission.

## Install and remove

Review the contents, then install the exact file:

```sh
sudo apt install "$HOME/edex-packages/edex-ui-tui_0.1.0~alpha1-1_all.deb"
edex-ui-tui --cwd "$HOME"
edex-ui-tui --toggle-keyboard
edex-ui-tui --install-shell-frame
```

Launch from your graphical desktop. The command opens a dedicated local Kitty window with temporary-file graphics. Controls target the existing project session. Set EDEX_TMUX_SOCKET to a separate value for isolated tests, and use that value for controls too.

The launcher uses /usr/bin/python3 on Ubuntu. Shared staging keeps /usr/bin/python as the Arch default. Runtime files live in /usr/share/edex-ui-tui, documentation and licenses in /usr/share/doc/edex-ui-tui, and the manual in /usr/share/man/man1. We add no service or maintainer script and change no user shell, tmux or Kitty configuration.

An upgrade preserves running shells but does not reload Python workers. Finish work, stop the session, and launch again to load the new version. Removal also leaves an existing session running until you stop it:

```sh
edex-ui-tui --stop
sudo apt remove edex-ui-tui
```

## Validation

Run the portable package tests, Debian checks and runtime suite:

```sh
python3 tests/test_provenance.py
python3 tests/test_packaging.py
python3 tests/test_debian_package.py
python3 tests/run.py
```

The Debian tests build twice and compare bytes, inspect root ownership and file modes, verify asset digests, load extracted runtime modules and reject maintainer-field injection. CI runs these checks on both configured Python versions. The shared staging test compares Arch and Ubuntu runtime bytes; only the launcher interpreter changes.

On 2026-10-26 we passed the full Ubuntu runtime suite and tested installation, upgrade from a local revision fixture, package integrity, restarted workers, frame rendering, keyboard hide/show and removal. We verified 37 asset/font digests. The isolated test preserved the prior review session's native shell PIDs and checked user config hashes. A WSLg capture showed the opaque shell surface, clipped corners, instruments and enlarged keyboard. We keep that capture private because it contains local machine details.

The minimal test distro excludes documentation through its dpkg configuration. We included this package's doc path for the test installation with a command-specific dpkg --path-include option. We left the distro's global filters unchanged. A normal Ubuntu installation may not have those filters.

The final lint run reports no errors and one warning: initial-upload-closes-no-bugs. We added the manual page after the initial check; the changelog warning needs no invented bug number. Keep popup movement/resize overlap, direct-transfer reattach, multiple clients and physical touch in the alpha limitations described in the existing release notes.

## Release checkpoint

Keep the Ubuntu artifact and its checksums separate from the frozen Arch bundle. Review the Ubuntu commit, CI and package contents before attaching a binary to a prerelease. Publishing, tagging and merging remain separate steps. Test native Ubuntu and other distro versions before widening support claims.
