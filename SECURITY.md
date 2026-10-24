# Security policy

## Reporting

Report vulnerabilities through this repository’s GitHub Security tab using **Report a vulnerability**. Include the affected revision, versions, reproduction steps, and the impact you observed. Use test files and invented input. Do not send credentials, shell history, or private captures.

We maintain the current main branch. We have no stable release series or guaranteed response time yet. The security-patched upstream fork provides our reference; its name does not establish an audit of this port.

## Scope and trust boundaries

You run the port as your Linux user. It launches shells, reads Linux metrics, opens files through Yazi, and sends graphics to attached terminals. Treat the repository, tmux configuration, terminal, Yazi plugins, and configured file openers as trusted local code. Run it without root privileges.

Review terminal and mouse input, tmux pane identifiers, paths and filenames, image data, local runtime files, subprocess arguments, and terminal responses as potential inputs across boundaries. A file opener can execute programs with your permissions. The port does not provide a sandbox for shells or files you open.

## Properties to preserve

- Limit session operations to this project's isolated tmux server. Check the selected shell marker before routing keyboard input.
- Route on-screen keys to the selected marked shell. Do not record typed content or introduce global keyboard hooks.
- Upload file icons only to same-user character terminals attached to this project's server. Keep terminal probe replies out of shell input.
- Create runtime locks with ownership checks and reject symlink targets. Clean up only the image IDs, test processes, and temporary files this project owns.
- Keep argument boundaries intact when passing paths or input to subprocesses. Do not treat filenames or untrusted terminal responses as shell commands.
- Keep metrics local. Do not add telemetry or external endpoint lookup without documenting it and obtaining the user's choice.

These are requirements for reviewers, not claims that a security audit has proved each control.

## Findings and limitations

Report command injection, input routing to the wrong session, cross-user terminal writes, unsafe local file handling, or leaks of typed content or private data. Include a reachable path and impact. We have not established exclusions or accepted-risk exceptions for these classes.

We have not verified tablet clients, Mosh transport, or multiple-client behavior. External terminal applications can emit graphics outside our writer lock. Assess failures in context; a visual glitch can become a security issue if it sends unintended input or exposes private content.

For upstream or dependency vulnerabilities, report to the relevant maintainer too. Explain how the port reaches the affected behavior so we can assess our exposure.
