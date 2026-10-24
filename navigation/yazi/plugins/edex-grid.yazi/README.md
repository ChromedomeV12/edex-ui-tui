# eDEX filesystem grid

Scoped UI plugin for Yazi 26.9.1. Current renders cards; Yazi owns enumeration, sorting, filtering, selection and file operations. Original eDEX SVG icons are loaded by file_icons.py through Kitty placeholders. No second directory scanner runs alongside Yazi.

Read [the navigation guide](../../../../docs/FILE-NAVIGATION.md). Use arrows to move through the grid, Enter to open the highlighted file or folder, and Backspace to go up. Click a card to highlight it. Use native Yazi actions for file operations. The header and footer show your directory and position; batch marks remain separate from the highlight.

Root / and Go up are shortcuts on the first page, not entries in Yazi's file cursor. Grid drawing, hit testing and key movement share model functions; tests/test_grid.lua checks geometry/boundaries and tests/test_yazi_navigation.py runs real Yazi against temporary fixtures and a recording opener in a private tmux server.

navigator.py preserves its child lifetime and reloads original icon assets for new attached clients. File-pane passthrough remains disabled so terminal probe replies cannot reach the shell. Normal Yazi configuration is untouched. librsvg supplies SVG rasterization; other Yazi releases and tablet clients need separate validation.
