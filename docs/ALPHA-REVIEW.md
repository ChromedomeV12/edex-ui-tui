# Local alpha review

Review date: 2026-10-26. Baseline: main at 6e82729. Scope: the experiment branch through its packaging checkpoints, plus the final provenance and documentation changes in this review.

Outcome: no remaining blocker found in the reviewed single-client local workflow. The draft v0.1.0-alpha.1 notes keep popup movement, remote transport and untested input paths outside its tested scope. Main remains unchanged.

## Runtime and package paths

| Area | Review and evidence |
| --- | --- |
| Entry point and session selection | Reviewed app.py, launch.py and workspace bindings. Argument lists preserve path boundaries. Controls select the named server and retain its transport. Isolation tests cover overlapping servers and a server that predates launch. |
| Shell and input preservation | Reviewed workspace locking, slot switching and keyboard routing. The keyboard checks the selected shell's random token and pauses behind a modal. Recorder tests exercise taps without executing input. Resize and installed-upgrade checks preserve native shell PIDs. |
| File navigation | The branch retains the native Yazi action model; its Lua change adjusts colors. Reviewed navigator and icon routing, including same-user character-terminal checks and the file pane's disabled passthrough. Existing grid navigation and file activation checks pass. |
| Graphics and frame cleanup | Reviewed bounded temporary-file transfer, image-scoped deletion, metadata heartbeats, frame masking and bootstrap recovery. Tests cover stalled consumption and cleanup. Direct-transfer reattach remains a known limitation. |
| Layout and raster work | Reviewed reflow, keyboard geometry, palette roles and the globe/text caches. Resize integration checks and pixel comparisons support those changes. Runtime Pillow internals retain a tested public fallback. |
| Package contents | Reviewed the explicit runtime module list, resource selection, entry point and license placement. Runtime staging excludes tests, capture collections, Git metadata and diagnostic probes. The clean build imports all 20 installed modules and verifies the declared artifacts. |
| Development-only code | The standalone border probe and profiler remain in source for reproduction. The installed package excludes them; it includes border_frame.py because the shell frame imports its geometry helpers. |

The prior full integration runs, clean Arch build and installed-upgrade results appear in validation. This review does not expand those checks into support for other clients or transports.

## Corrections from review

The earlier package-lint pass found a license-directory mismatch. Commit 10e766a corrected it to the actual preview package name, and the clean-build and upgrade checks verified the migration.

The final asset pass found two stale derived-source hashes from CRLF working copies: keyboard CSS and the keyboard class. We corrected them using the pinned upstream Git blobs. We also added bundled digests for the measured keyboard geometry and arrow data, and added verification for the three fonts and OFL file. The checks now cover 37 bundled artifacts. These changes alter metadata and test coverage, not asset pixels or layout data.

We replaced the older README layout image with a cropped capture from the current interface. A private capture fixture supplied synthetic counters, a neutral shell and sample files. The renderer and input/layout code stayed unchanged. The caption identifies the fixture data. We inspected the image for private addresses, machine paths and personal file listings; its PNG metadata contains no additional fields. The separate keyboard image comes from the current renderer. Neither capture proves performance or physical touch support.

## Publication boundary

The release notes and current screenshots are ready for a local alpha. The existing -git recipe tracks the experiment branch; a fixed release recipe and source archive must identify the exact reviewed commit before a tag or public package. No merge, tag or AUR submission has occurred. Follow RELEASE-CHECKLIST.md for the publication steps.
