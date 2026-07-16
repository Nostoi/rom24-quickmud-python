# Session Summary — 2026-07-16 — Autonomous 10-iteration loop retrospective

## Scope

Final iteration (10/10) of the user-commissioned autonomous parity loop
("continue with the next session then loop 10 times"). This iteration:
stray-db cleanup, carry-over triage (all three correctly remain deferred),
and this retrospective — the single review surface for the whole run.

## The run at a glance (v2.14.322 → v2.14.331)

| Iter | Closed | Commit(s) | One-liner |
|------|--------|-----------|-----------|
| 1 | **DB-005** (HIGH) | `29e9f99d` | Area resets process per room in ascending room-vnum order (ROM `reset_area`/`load_resets`), fixing world population where global M-limits bind mid-area AND boot creation order (char_list order for INV-045 walks). |
| 2 | **FIGHT-098** | `dee59869` | `mob_hit`'s OFF_AREA_ATTACK sweep walks ROM's global char_list domain from the room-head seed; FIGHT-095's helper promoted to shared `char_list_walk_from_room_head`. |
| 3 | **GL-050** + **FIGHT-099** | `e2ba759d` | GL-050 probed vs the live C oracle: aggr victim selection was never divergent (DB-005 contamination). Residual: link-dead PC auto-recall missing from `damage()`'s epilogue — fixed; harness driver-descriptor fidelity fixed. |
| 4 | **FIGHT-100** | `58c955f7` | Wimpy auto-flee legs of `damage()`'s epilogue (NPC ACT_WIMPY low-hp, charmed-absent-master, PC `hit <= wimpy`). |
| 5 | **FIGHT-101** | `93fcba45` | `do_flee`'s non-ROM wait-gate + WAIT_STATE removed — ROM gates wait only at the descriptor input loop (already mirrored by `connection.py`). |
| 6 | **FIGHT-102** | `63a27c23` | Same non-ROM wait-gate removed from six sibling commands (kick/rescue/backstab/bash/berserk/cast); class locked by a Layer-A grep-guard. |
| 7 | **FIGHT-103** + 3 C-oracle scenarios | `8f782125`, `c04f1f29` | Fleer output channel fixed (look-before-flee-lines + epilogue delivery). Scenarios: DB-005 census, FIGHT-098 domain (mutation-tested), FIGHT-100 wimpy-flee. New mirrored directives: `__mob_census` (py), `__mob_fight`, `__char_fight`. |
| 8 | **FIGHT-094** | `0fe87f8f` | `check_killer` inside `damage()` at ROM's position (before set_fighting) — first PvP hit PK-flags through any damage path. |
| 9 | **HANDLER-009** | `bdd45e6c` | `MobInstance.move_to_room` head-inserts via `Room.add_mob` (ROM `char_to_room`). |
| 10 | cleanup + retrospective | (docs) | Stray `data/quickmud.db` / `doc/game.db` deleted (untracked debris). Carry-over triage below. |

**Totals**: 11 gaps closed (DB-005, FIGHT-094/098/099/100/101/102/103,
GL-050, HANDLER-009 — FIGHT-099..103 were *discovered* during the loop),
3 C-oracle scenarios + 3 staging directives added, tests 6218 → **6244
passed** (differential 97/97 → **102/102 across 69 scenarios**), ~19 local
commits, version 2.14.322 → **2.14.331**.

## Cross-cutting findings

- **DB-005 was load-bearing**: its boot-order fix retroactively explained
  GL-050's "divergent victim selection" (RNG-stream contamination) — a
  reminder that population-order bugs masquerade as downstream RNG bugs.
- **The `damage()` epilogue was wholesale missing** (fight.c:978-1012):
  link-dead recall (FIGHT-099), wimpy flees (FIGHT-100), and the
  `check_killer` call (FIGHT-094) all lived there. One ROM read closed
  three gaps across three iterations.
- **The non-ROM wait-gate class** (7 commands) came from a
  misunderstanding: ROM gates wait at the descriptor loop, never
  in-function; `connection.py` already mirrored the ROM mechanism, making
  every in-function gate a double-count. Locked by grep-guard.
- **Harness fidelity matters**: the Python replay driver read as link-dead
  (no desc) until iteration 3 — any desc-gated ROM path would have silently
  desynced every scenario.

## Carry-over triage (iteration 10)

- **DESC-001** — remains ⏳ OPEN **by design** (latent, unreachable within
  ROM's `MAX_INPUT_LENGTH`; removing the guard trades a safety cap for zero
  parity benefit). Already durably documented in `ACT_INFO_C_AUDIT.md`.
- **OLC spell-name lookup** — deferred inside OLC_ACT-009's ✅ row, gated on
  a skill-by-index registry (real infra, not a quick close).
- **IS_BUILDER** — part of OLC_ACT-002 (`redit create <vnum>`), a
  substantial missing feature; wrong shape for an end-of-loop close.
- **Stray db files** — deleted (`data/quickmud.db` 0-byte, `doc/game.db`
  Sep-2025 stale; both untracked/ignored, no repo diff).

## Operator actions requested

1. **Review + push**: ~19 local commits on `master`
   (`29e9f99d`…HEAD), version 2.14.331, CHANGELOG `[Unreleased]` fully
   describes the run. Publish to PyPI at your discretion.
2. Known infra nuisance (pre-existing, documented): intermittent xdist
   worker-crash INTERNALERROR on single full-suite runs — layers verified
   separately throughout (unit 2801 + integration 3443 green).

## Next Steps (post-loop backlog)

OLC_ACT-002 (`redit create`) is the largest well-specified remaining item;
the OLC spell-name lookup wants a skill-by-index registry first. The
divergence-class roster (`/rom-divergence-sweep`) is the standing default
when no named gap is queued.
