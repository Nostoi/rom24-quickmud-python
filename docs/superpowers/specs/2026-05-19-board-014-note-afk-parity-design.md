# BOARD-014 Note AFK Parity Design

## Goal

Close `BOARD-014` by mirroring ROM `src/board.c` AFK behavior during note composition as closely as QuickMUD's request/response note flow allows.

## ROM Source

- `src/board.c:49`
- `src/board.c:503`
- `src/board.c:1175-1182`

ROM behavior:

- entering note-writing puts the player AFK
- posting or forgetting the note exits that state
- the AFK state is tied to the note-editor lifecycle

## Current Python State

- QuickMUD stores note composition in `pcdata.in_progress`
- QuickMUD already supports `CommFlag.AFK`
- prompt and `who` output already respect `CommFlag.AFK`
- QuickMUD does **not** use ROM's modal `CON_NOTE_*` descriptor state machine

## Design

Use `pcdata.in_progress` as the Python ownership boundary for note-editor AFK.

### Ownership rule

Add a boolean ownership field to `NoteDraft`:

- `set_afk: bool = False`

Meaning:

- `True`: note-writing set `CommFlag.AFK`, so note completion/cancellation owns clearing it
- `False`: player was already AFK before note-writing started, so note completion/cancellation must not clear it

### Command behavior

#### `note write`

- if no draft exists or a fresh draft is created, and `CommFlag.AFK` is not already set:
  - set `CommFlag.AFK`
  - set `draft.set_afk = True`
- if `CommFlag.AFK` is already set:
  - leave it set
  - set `draft.set_afk = False`

#### `note send`

- preserve existing post behavior
- if the draft owns AFK (`set_afk=True`), clear `CommFlag.AFK`
- if the draft does not own AFK, leave `CommFlag.AFK` untouched

#### `note forget`

Add a new subcommand mirroring ROM finish-menu cancel:

- requires an in-progress draft on the current board
- discards the draft
- clears `CommFlag.AFK` only when `set_afk=True`
- returns ROM-style cancellation text

### Lost-link draft handling

Keep the existing `BOARD-011` behavior:

- `note write` still discards a stale textless draft first
- if that stale draft owned AFK, clear it before replacing the draft

## Non-goals

- do not add modal descriptor `CON_NOTE_*` states
- do not change unrelated AFK command behavior
- do not broaden board command vocabulary beyond `note forget`

## Tests

Add/extend parity tests for:

- `note write` sets AFK when previously clear
- `note write` preserves pre-existing manual AFK
- `note send` clears note-owned AFK
- `note send` preserves manual AFK
- `note forget` clears note-owned AFK
- `note forget` preserves manual AFK

## Rationale

This is the closest 1:1 parity mapping available without replacing QuickMUD's non-modal note architecture. The visible ROM contract is preserved on the live player state surface (`AFK`, prompt, `who`, tells) while keeping ownership precise enough to avoid clearing manually enabled AFK.
