# Linux alpha packaging

Arch preparation lives on experiment/kitty-borders. The experiment/ubuntu-alpha branch adds a local Ubuntu binary package using the same runtime and asset staging. See [Ubuntu alpha packaging](UBUNTU-ALPHA.md) for dependencies, build commands and installed checks. Neither preparation publishes a release or an AUR package.

## Arch preview

The recipe in packaging/arch/PKGBUILD prepares an edex-ui-tui-git package from the experiment branch. It is a development recipe. We have not submitted it to AUR or tagged a release. It follows a moving branch; record the commit shown by makepkg when reporting a problem.

The prepared v0.1.0-alpha.1 recipe lives in packaging/arch-release, with generated .SRCINFO. It builds edex-ui-tui 0.1.0alpha1-1 from source commit d20f666 and a fixed archive checksum. Its download URL will work after the prepared source asset is published. Until then, place the matching edex-ui-tui-0.1.0-alpha.1.tar.gz beside that recipe to reproduce the build. The clean-root build used that local archive and verified its checksum before extracting it.

We use the [Arch PKGBUILD format](https://man.archlinux.org/man/PKGBUILD.5.en) for dependencies, checks and staging. The VCS source uses SKIP for the archive checksum; the bundled artifact check still verifies the files listed in UPSTREAM.json. A release recipe should use a reviewed tag or commit and an archive checksum.

## Build and inspect

Use a disposable Arch environment with base-devel and git. From the preview checkout:

```sh
cd packaging/arch
makepkg -s
pacman -Qlp ./*.pkg.tar.zst
```

Read the recipe before building. makepkg runs the portable renderer, provenance and packaging checks. It does not run the complete desktop integration suite. Use python3 tests/run.py from the source root for that checkpoint.

After reviewing the contents, install the selected package with sudo pacman -U followed by its exact filename. Do not install several old build files with a wildcard. Use sudo pacman -R edex-ui-tui-git to remove it. Removing a package does not stop an existing tmux session; finish your work and run edex-ui-tui --stop first if you want to end that session and its shells.

## Installed paths

| Path | Contents |
| --- | --- |
| /usr/bin/edex-ui-tui | Launcher |
| /usr/share/edex-ui-tui | Runtime modules, project configs, assets, reference data and notices |
| /usr/share/applications/edex-ui-tui.desktop | Desktop menu entry using the system terminal icon |
| /usr/share/doc/edex-ui-tui | Text documentation |
| /usr/share/licenses/edex-ui-tui-git | GPL, third-party notices and bundled font license, under the preview package's actual name |

The fixed release package uses /usr/share/licenses/edex-ui-tui for its license files. Runtime and command paths stay the same. The fixed package conflicts with edex-ui-tui-git because both own the same application files.

The staging script uses a list of runtime modules and resource types. It excludes Git metadata, tests, diagnostic probes, captures and Python caches. It retains reference files because runtime palette/background generation and provenance use them. We install no fonts into the system font directory and edit no user profile, normal Kitty config, tmux config or compositor rules. The package has no install hook or service.

## Launch and control

Run edex-ui-tui from a graphical Linux desktop. The command opens a dedicated Kitty window with the dotted preset and local temporary-file graphics. It clears the invoking tmux identity for that new window. It forwards launcher arguments as separate arguments, including paths with spaces. Leave enough screen space for at least 140 columns by 40 rows; a tiling compositor can make a second window too narrow even when Kitty requests a larger initial size.

```sh
edex-ui-tui --skip-intro --cwd "$HOME"
edex-ui-tui --toggle-keyboard
edex-ui-tui --install-shell-frame
edex-ui-tui --help
```

The help and session controls run without creating another Kitty window. The clipped frame remains an opt-in control on this experiment branch. The normal five shell slots and hidden-on-start keyboard keep their existing behavior. The default animation target stays 24 FPS.

Keep EDEX_TMUX_SOCKET consistent between launch and controls when using a separate test session. The default targets the project's per-user socket. Reattaching keeps the existing workers; an update does not reload their Python code. Finish your work before stopping and restarting after an upgrade.

This command starts a local window. For remote SSH experiments, launch the remote source in a compatible terminal with direct graphics transfer; do not forward temporary-file mode across filesystems. Mobile SSH, Mosh and direct-transfer reattach remain separate validation work.

## Release gates

Before AUR submission, build in a clean Arch build environment, review dependencies and licenses, inspect the package, and test installation and removal in the disposable VM. Review the experiment for merging and decide whether the first release includes or defers popup movement/resize occlusion. Keep unverified input and remote-client paths out of support claims. A successful staged build alone does not establish package-manager installation or upgrade behavior.

On 2026-10-25 we built the recipe in the prepared Omarchy VM using a local VCS fixture, then inspected, installed, launched and removed the package. The first-show keyboard, instrument columns, tabs, Yazi and opt-in clipped frame appeared in the installed window. The checked user configs and original review session stayed intact. See [validation](VALIDATION.md) for the source-export and graphics fixes this exposed. We still need a clean Arch build, package upgrade checks and final review before AUR submission.

On 2026-10-26 the clean Arch build and upgrade checks passed for commit 10e766a. We used Arch's [makechrootpkg workflow](https://man.archlinux.org/man/makechrootpkg.1.en) with an Arch-only base-devel root and the 2026-10-25 repository snapshot. The recipe's 23 checks passed. Namcap reported zero errors; its 46 warnings and their scope appear in validation. An installed upgrade preserved the idle shell and migrated the license directory, and we inspected a fresh graphical session before removing the test package. Final branch and release-content review remain; follow [the release checklist](RELEASE-CHECKLIST.md).
