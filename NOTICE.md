# Credits and licenses

## eDEX-UI

Gabriel “Squared” Saillard and the eDEX-UI contributors created the original application. The upstream package records Copyright © 2017–2021 Gabriel 'Squared' SAILLARD. Rob “arscan” Scanlon created the globe reference used upstream.

We adapt the interface and assets from theelderemo/eDEX-UI-security-patched at commit d59e5e287d9ebde8920aaf638ae7e685115c3de4 under GPL-3.0. UPSTREAM.json records copied files and derivations. We retain selected reference source under references/ for comparison. The port uses Python, Kitty graphics, tmux, and a custom Yazi view in place of the upstream Electron renderer.

Read LICENSE for the GPL version 3 terms. Preserve this notice and third-party license files when distributing copies. This project has no affiliation with Disney, TRON, GitSquared, or the upstream fork maintainers. TRON and ENCOM names and imagery belong to their respective rights holders; we claim no trademark rights.

## Fonts

We bundle Rajdhani Light, Medium, and SemiBold from google/fonts under the SIL Open Font License 1.1. See assets/fonts/OFL.txt and assets/fonts/SOURCE.json for the copyright notice, revision, and hashes. Supply your own licensed United Sans files if you want to use them; we do not distribute them.

## Kitty placeholder data

We retain the published row/column diacritic mapping and its header in assets/rowcolumn-diacritics.txt. It describes its derivation from Unicode 6.0.0 data. See the Kitty graphics protocol documentation for placeholder semantics.

## Yazi integration

We provide the edex-grid plugin under GPL-3.0. Yazi, tmux, Kitty, Pillow, and librsvg remain separate dependencies with their own licenses. We do not vendor their executables here.
