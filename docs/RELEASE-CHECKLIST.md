# First local alpha review

Arch preparation is complete and remains unpublished. The separate experiment/ubuntu-alpha branch adds the first Ubuntu 24.04 binary package. Read [its build and validation record](UBUNTU-ALPHA.md) before combining artifacts in a release; the Ubuntu source commit differs from the frozen Arch archive because it adds packaging and documentation.

The prepared alpha source is commit d20f6669b2dad1b315b37ab9ff2cbfbc1f8b17f3 on experiment/kitty-borders. Later preparation commits add the fixed Arch recipe and publication records. Main retains the earlier baseline. We have not tagged a release or submitted a package to AUR. Read [validation](VALIDATION.md) for the environments, measurements and limits behind this checklist.

## Completed checks

- Full integration suites on Omarchy and Ubuntu, with CI on Python 3.11 and 3.13.
- Visual checks for the larger keyboard, arrow alignment, instrument typography, actual window resize and a second font scale.
- Pixel-equivalence checks for the raster optimizations; ten-minute local stability check at 30 and 24 FPS targets. The default remains 24.
- Clean Git export launch and scoped stop, preserving the separate working review session.
- Arch-only clean package build of the published candidate, with all 23 recipe checks passing.
- Package staging checks for all 20 runtime modules, the 31 declared assets, argument handling and package-named license files.
- Installed upgrade from the earlier local fixture, license-directory migration, package integrity check and restarted graphical session.
- Removal of the test package with the original review session and checked user configs intact.
- Final diff review, current public captures with fixture data, and draft v0.1.0-alpha.1 notes.
- A fixed source archive, checksum-pinned Arch release recipe and generated .SRCINFO. The fixed package passed all 24 recipe checks in the clean root; installed checks loaded 20 modules and verified 37 artifact digests.

Namcap has no remaining errors. Its warnings cover private-directory Python imports, an implicitly satisfied shell dependency and four runtime dependencies that its static scan questions. We retained the warnings and the supporting checks in validation.

## Remaining release work

The [final alpha review](ALPHA-REVIEW.md) covers the experiment diff, package contents and current screenshots. The [draft release notes](releases/v0.1.0-alpha.1.md) define the local workflow and retain popup movement, remote graphics and untested input limitations. Review preparation is complete; merging, tagging and publication remain separate steps below.

1. Accept the reviewed local-alpha scope and merge the experiment without discarding the reviewed source commit. The tested path is one local Kitty client with tempfile graphics. Keep popup movement/resize overlap and untested input/remote paths in the release limits.
2. Create v0.1.0-alpha.1 at d20f6669b2dad1b315b37ab9ff2cbfbc1f8b17f3. The source archive identifies that commit; later packaging-only commits do not change its runtime. Rebuild the archive and update the recipe checksum if choosing another source commit.
3. Publish the prerelease with the prepared source archive, Arch package, checksums and release notes. The recipe expects edex-ui-tui-0.1.0-alpha.1.tar.gz as an uploaded release asset. GitHub's generated source download has different archive bytes and cannot replace it under the same checksum.
4. Check AUR name availability and maintainer details, then submit PKGBUILD and .SRCINFO from packaging/arch-release after the source URL exists. Verify the generated metadata again if changing package fields. Local preparation does not publish an AUR package.

The fixed Arch alpha is edex-ui-tui 0.1.0alpha1-1. The earlier 0.r22.g10e766a-1 artifact remains a VCS preview. Updating files does not reload existing Python workers. Finish shell work, stop the project session, and launch new workers after an upgrade.

After the local alpha, continue the separate film-boardroom interpretation, remote graphics and mobile input research, then Yazi/shell convenience actions. Keep those additions separate from packaging fixes.
