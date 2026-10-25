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

## Augmented UI corner geometry

The standalone border probe adapts the `tr-clip` and `bl-clip` outer and inner polygons from augmented-ui 1.1.2. This legacy stylesheet matches eDEX's `augmented-ui="bl-clip tr-clip exe"` markup; the pinned fork's lockfile lists version 2.0.0, which uses a different stylesheet name and interface. See UPSTREAM.json for the source and checksum.

```text
BSD 2-Clause License

Copyright (c) James0x57, PropJockey, 2019
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
