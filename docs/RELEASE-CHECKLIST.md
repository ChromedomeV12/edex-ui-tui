# First local alpha review

The packaging candidate is commit 10e766a on experiment/kitty-borders. Main retains the earlier baseline. We have not tagged a release or submitted a package to AUR. Read [validation](VALIDATION.md) for the environments, measurements and limits behind this checklist.

## Completed checks

- Full integration suites on Omarchy and Ubuntu, with CI on Python 3.11 and 3.13.
- Visual checks for the larger keyboard, arrow alignment, instrument typography, actual window resize and a second font scale.
- Pixel-equivalence checks for the raster optimizations; ten-minute local stability check at 30 and 24 FPS targets. The default remains 24.
- Clean Git export launch and scoped stop, preserving the separate working review session.
- Arch-only clean package build of the published candidate, with all 23 recipe checks passing.
- Package staging checks for all 20 runtime modules, the 31 declared assets, argument handling and package-named license files.
- Installed upgrade from the earlier local fixture, license-directory migration, package integrity check and restarted graphical session.
- Removal of the test package with the original review session and checked user configs intact.

Namcap has no remaining errors. Its warnings cover private-directory Python imports, an implicitly satisfied shell dependency and four runtime dependencies that its static scan questions. We retained the warnings and the supporting checks in validation.

## Remaining release work

1. Review the experiment diff against main. Check session isolation, file opening, graphics cleanup and the package file list. Keep private captures, credentials, commercial fonts and local deployment records out of release artifacts.
2. Review the public screenshots and usage text against the final candidate. Existing screenshots predate some layout changes. Replace them only with captures that omit private paths, addresses and file listings.
3. Review the first alpha's scope. The tested path is one local Kitty client on a shared filesystem with tempfile graphics. The native process popup remains rectangular; its frame mask tracks the opening rectangle and does not establish correct occlusion while moving or resizing it.
4. Write release notes that state these limits. Keep direct-transfer reattach, multiple clients, physical touch and mobile/Mosh support outside the supported workflow until their checks pass. Startup tests do not establish complete upstream choreography or movie fidelity.
5. Review merging, choose a release version and tag the reviewed commit. Prepare a release recipe with a fixed source and checksum before public distribution. The current -git recipe follows the experiment branch.
6. Review the AUR metadata and generate .SRCINFO from the final recipe. Submit it after the release review; do not treat a successful local build as publication.

The clean-built candidate is 0.r22.g10e766a-1. That is a VCS preview version, not the first release number. Updating files does not reload existing Python workers. Finish shell work, stop the project session, and launch new workers after an upgrade.

After the local alpha, continue the separate film-boardroom interpretation, remote graphics and mobile input research, then Yazi/shell convenience actions. Keep those additions separate from packaging fixes.
