# Development guidance

Read README.md, CONTRIBUTING.md, and SECURITY.md before changes. Use the stop-slop writing guidance for project prose: direct language, specific claims, active voice, and no filler. Preserve verbatim license texts and third-party notices.

Keep main as the reviewed baseline. Use the experiment/kitty-borders branch and a separate worktree for border exploration. Do not deploy experiments into the working VM session. Test on the disposable Omarchy VM first; defer Ubuntu and physical-host changes until the owner asks.

Keep native tmux shells, five shell slots, the optional keyboard, and the isolated Yazi configuration. Clicking highlights file cards; arrows move through the grid; Enter opens; Backspace goes up. Do not add fictional headings or global keyboard hooks.

Preserve the 24 FPS target, stable graphics IDs, serialized multipart writes, and metadata-only placement heartbeats. Reserve cell repaints for initialization or recovery. Inspect actual captures after rendering changes.

Retain GPL notices, UPSTREAM.json provenance, and font licenses. Do not commit commercial fonts, credentials, personal paths, shell input, captures with private data, or local deployment records. Check the staged diff and assets before publication.
