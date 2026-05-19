# BOARD-014 Note AFK Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mirror ROM `board.c` note-editor AFK behavior in QuickMUD's request/response note flow, including a cancel path.

**Architecture:** Use `pcdata.in_progress` as the note-editor lifecycle anchor. Track whether note composition owns the AFK flag on `NoteDraft`, then clear that flag only on note-owned exit paths (`send` / `forget` / stale-draft replacement).

**Tech Stack:** Python dataclasses, command dispatcher, pytest integration tests, ROM `src/board.c` parity rules.

---

### Task 1: Add failing BOARD-014 parity tests

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_boards_rom_parity.py`

- [ ] **Step 1: Write failing tests**

Add tests for:
- `note write` sets `CommFlag.AFK`
- `note send` clears note-owned AFK
- `note forget` clears note-owned AFK
- manual AFK survives `note send`
- manual AFK survives `note forget`

- [ ] **Step 2: Run the focused test slice and verify it fails**

Run:

```bash
./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_boards_rom_parity.py -k 'afk or forget'
```

Expected:
- failing assertions for missing AFK transitions
- unknown/help behavior for missing `note forget`

### Task 2: Implement note-owned AFK tracking

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/models/board.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/notes.py`

- [ ] **Step 1: Add draft ownership field**

Add `set_afk: bool = False` to `NoteDraft`.

- [ ] **Step 2: Implement minimal AFK helpers**

Add local helpers in `mud/commands/notes.py` to:
- set note-owned AFK on draft creation
- clear note-owned AFK on draft exit

- [ ] **Step 3: Wire `note write`, `note send`, and `note forget`**

Behavior:
- `note write` sets AFK only when not already AFK
- `note send` clears only note-owned AFK
- `note forget` clears only note-owned AFK and discards draft
- stale textless draft replacement also clears note-owned AFK before replacing

- [ ] **Step 4: Re-run focused board parity tests**

Run:

```bash
./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_boards_rom_parity.py -k 'afk or forget'
```

Expected:
- pass

### Task 3: Verify board and AFK surfaces

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/BOARD_C_AUDIT.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
- Create: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-19_BOARD_014_NOTE_AFK_PARITY.md`

- [ ] **Step 1: Run targeted regression band**

Run:

```bash
./venv/bin/python -m pytest -q \
  /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_boards_rom_parity.py \
  /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_boards.py \
  /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_act_comm_rom_parity.py \
  /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_who_command.py \
  /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_prompt_rom_parity.py
```

Expected:
- all pass

- [ ] **Step 2: Run full-suite fail-fast check**

Run:

```bash
./venv/bin/python -m pytest -q --maxfail=1
```

Expected:
- suite stays green

- [ ] **Step 3: Update audit/session docs**

Record:
- `BOARD-014` closed
- tests added
- full-suite result
