# Session Status — 2026-06-01 — FIGHT-040 dirt-kick already-blinded (2.12.47)

## Current State

- **Active mode**: cross-file invariants — the **INV-025 manual-room-loop PERS
  sweep is now DRAINED for magic** (`$n`-only single-actor spell room lines).
- **Today's progression (all pushed green):**
  - 2.12.40 → 2.12.42: CAST-009 + TRAIN-005 (full suite 5242).
  - 2.12.42 → 2.12.44: MAGIC-012 (frenzy) + MAGIC-013 (cure_disease) —
    manual-room-loop `$n`/`$s` PERS + channel (full suite 5246).
  - 2.12.44 → 2.12.45: **MAGIC-014** (`ed9b35e0`) — batch closure of the ~11
    `$n`-only single-actor spell room lines (haste, slow ×2 legs,
    giant_strength, stone_skin, pass_door, sleep, weaken, earthquake,
    create_rose) → `act_to_room`; fixed the visible-NPC "Someone" bug
    (`if name else "Someone"` ternaries) + invisible-actor leaks. Full suite
    **5249 passed, 4 skipped** (no-xdist reliable mode).
  - Probed group/follower + affect-tick engine — both **faithful**.
  - 2.12.45 → 2.12.46: **FIGHT-039** (`83e42d33`) — `trip` self-trip lines
    now carry `{5..{x` colour + `$n` PERS + `$s` possessive (ROM
    `fight.c:2699-2701`); also fixed the missing colour on the self line. Full
    suite **5251 passed, 4 skipped**.
  - 2.12.46 → 2.12.47: **FIGHT-040** (`4015cccb`) — dirt-kick already-blinded
    check now uses ROM's gendered `$E` message ("He's/She's/It's already been
    blinded."), in ROM's order (AFF_BLIND before self-check), with the
    Python-invented "dirt kicking" guard deleted (dead code). Confirmed the
    "already has dirt in their eyes" line was Python-invented. Full suite
    **5256 passed, 4 skipped**.
  - **Re-probe outside `handlers.py`** found ~10 baked-name `room.broadcast`
    sites in `mud/commands/` (advancement/session/notes) that bypass
    `act_to_room` PERS masking — confirmed vs ROM `act()` lines, filed as a NEW
    OPEN SWEEP in the INV-025 trail (not yet fixed).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_MAGIC014_SINGLE_ACTOR_PERS_SWEEP.md](SESSION_SUMMARY_2026-06-01_MAGIC014_SINGLE_ACTOR_PERS_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.47 |
| Tests | **full suite green: 5256 passed, 4 skipped** (run `pytest -p no:xdist -o addopts="" -q`; under high load `-n auto` hangs at worker fork and `-n0` can hit a broken xdist `sessionfinish` teardown) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **INV-025 `mud/commands/` baked-name `room.broadcast` sweep** (~10 sites: advancement/session/notes — work-list in the INV-025 trail); `mud/combat/`, `mud/world/`, `communication.py` not yet re-probed |

## Next Intended Task

1. **INV-025 command-layer PERS sweep** — convert the ~10 confirmed
   `mud/commands/` baked-name `room.broadcast(f"{char.name} …")` sites to
   `act_to_room(room, "$n …", char, exclude=char)` (work-list + ROM refs in the
   INV-025 trail): `advancement.py` 191/196/360/377/400, `session.py`
   362/405/417, `notes.py` 377/457. Verify each ROM `act()` string (`$T`/`$s`
   tokens) first. Close as a batch (like MAGIC-014) — one suite + one push.
2. Re-probe `mud/combat/`, `mud/world/`, `mud/commands/communication.py` for the
   same baked-name `room.broadcast` pattern.
3. Other cross-file-invariants candidate areas (position transitions, mob script
   triggers) remain once the PERS sweep is exhausted.

> **Push note:** all of today's work (through 2.12.46) is pushed to `master`.
> **Stale index:** GitNexus reindex pending (the running one predates the
> MAGIC-012/013/014 + FIGHT-039 handler edits) — re-run on a quiet machine.
