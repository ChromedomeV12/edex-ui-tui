# File navigation

Click the filesystem pane to give it focus. The dark caption is the current card; `*` marks a file selected for batch operations. Moving the highlight does not open anything.

| Control | Action |
| --- | --- |
| Arrow keys | Left/right: adjacent card; up/down: one grid row |
| Enter | Enter the highlighted folder inside Yazi, or open only the highlighted file |
| Backspace / `h` | Go to the parent folder |
| `l` | Enter the highlighted folder |
| Click / tap a file card | Highlight it; no automatic opening |
| Mouse wheel | Move the highlight by rows |
| Page Up / Page Down | Move one grid page |
| Home / `g g`, End / `G` | First or last file |
| `j` / `k` | One grid row down/up, matching the arrows |
| Root /, Go up cards | Click shortcuts on the first page; not selectable files |
| `g /`, `g h` | Filesystem root, home directory |
| `g` then Space | Type a directory path to jump to |
| Space | Mark/unmark a file, then advance to the next card |
| `f`, then type | Filter the current folder by name; Enter accepts; Escape clears |
| `.` | Toggle hidden files |
| Escape | Clear selection/filter or dismiss a popup |

The header shows the folder you are browsing. The footer shows its current item count, page, highlighted filename and file position. Empty folders and zero filter results keep the navigation shortcuts available. On very small panes the grid switches to text cards and hides shortcuts if they cannot fit; Backspace and `g /` still work.

Native Yazi actions remain: `o` opens marked files (or the highlighted file); `O` chooses an opener; `y` copies, `x` cuts, `p` pastes, `r` renames, and `a` creates a file (end its name in `/` for a folder). `~` or F1 shows the full key guide. Files open using Yazi's configured editor/application; a terminal editor occupies the file pane until you exit it.

This browser has its own working directory. Browsing folders here does not run `cd` in a shell or follow changes in shell tabs. The eDEX on-screen keyboard remains linked to the central shell; use your physical/client keyboard or mouse for Yazi. Use Ctrl-b then an arrow to move focus between tmux panes; that prefix is separate from the plain arrows used inside the grid. Drag-and-drop is disabled because the native drag target logic assumes list rows; use `y`/`x` then `p` instead. The settings apply only to this eDEX session, not normal Yazi.
