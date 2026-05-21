# Parity Trust Rebuild Re-Audit Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild confidence in ROM parity by replacing weak smoke tests and over-broad certification claims with ROM-exact output, session-boundary, and runtime-path verification on the highest-risk user-visible surfaces.

**Architecture:** Treat this as a verification-program correction, not a feature project. The work proceeds in bounded slices: downgrade unsupported claims, tighten the verification standard, then re-audit the most user-visible and stateful ROM surfaces with exact comparisons against the C source and live server paths. A surface is not “verified” until ROM source, Python behavior, data inputs, and runtime path all agree.

**Tech Stack:** Python 3.10+, pytest, FastAPI/WebSocket test client, telnet server tests, SQLite (`mud.db`), ROM C source under `src/`, Markdown tracker docs under `docs/parity/` and `docs/sessions/`.

---

### Task 1: Roll back unsupported public certainty

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/README.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
- Test: none; verify by manual readback

- [ ] Remove or downgrade “100% verified/certified” wording that is not backed by ROM-exact evidence.
- [ ] Keep factual statements that remain true: green suite, audit-bound coverage, invariant coverage, current version.
- [ ] Add a short explanation that revalidation is in progress because live bugs exposed gaps in observable-behavior verification.

### Task 2: Define the stricter verification standard

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/ROM_PARITY_VERIFICATION_GUIDE.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Test: none; verify by manual readback

- [ ] Add explicit confidence tiers to the verification guide:
  - code/audit coverage
  - ROM-exact unit/output coverage
  - runtime-path coverage
  - data parity coverage
- [ ] State that “green suite” and “audited” are insufficient without user-visible ROM-exact assertions for commands and session boundaries.
- [ ] Add tracker notation or columns showing whether each surface has:
  - ROM source reviewed
  - golden-output assertions
  - runtime-path verification
  - data parity verification

### Task 3: Re-audit `act_info.c` and score-adjacent output surfaces

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ACT_INFO_C_AUDIT.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_player_info_commands.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_act_info_rom_parity.py`
- Test: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/act_info.c`

- [ ] Re-read `src/act_info.c` command by command for user-visible output wording, order, and conditional branches.
- [ ] Replace weak assertions (`len(output) > 50`, broad substring checks) with ROM-exact lines where practical.
- [ ] Prioritize:
  - `score`
  - `where`
  - `who`
  - `equipment`
  - `inventory`
  - `look` / room-description output if still only lightly asserted
- [ ] Any discovered drift gets a dedicated regression before the code fix.

### Task 4: Re-audit `nanny.c` / `save.c` session boundaries

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/SAVE_C_AUDIT.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_telnet_server.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_character_creation_runtime.py`
- Test: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/nanny.c`, `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/save.c`

- [ ] Verify full session boundaries under real server paths, not helper-only paths:
  - name → password → creation
  - creation completion → disconnect
  - reconnect → `Password:`
  - load → `reset_char` → `score`
  - save → reload → retained state
- [ ] Add explicit assertions for:
  - DB row after completed creation
  - post-login `logon` semantics
  - title/race/class on first command output after reconnect
- [ ] Treat direct helper tests as secondary evidence only.

### Task 5: Re-audit other high-risk user-visible command families

**Files:**
- Modify relevant audit docs and tests under:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/`

- [ ] Prioritize surfaces where players immediately notice drift:
  - healer/shop/train/practice
  - combat death messaging and aftermath
  - note/board flows
  - communication formatting (`say`, `tell`, `emote`, `pose`, `pmote`)
- [ ] For each family, classify existing tests as:
  - ROM-exact
  - smoke-only
  - missing runtime path
- [ ] Convert the smoke-only ones first.

### Task 6: Add a verification-debt checklist for every audit closure

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/ROM_PARITY_VERIFICATION_GUIDE.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/AGENTS.md`

- [ ] Require future audit closures to answer:
  - What exact ROM function was read?
  - What exact observable behavior was asserted?
  - Was the real server/runtime path exercised?
  - Was data parity checked if the surface depends on JSON/DB/tables?
- [ ] Do not allow “verified” wording in docs unless those answers exist.

### Task 7: Rebuild confidence conservatively

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/README.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/CHANGELOG.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`

- [ ] Only restore stronger parity language after the re-audit slices are complete.
- [ ] When restoring confidence statements, tie them to the stricter evidence tiers, not just test counts.
- [ ] Record each completed trust-rebuild slice in session summaries so later agents can see what was actually revalidated.
