# Session Summary — 2026-04-24

**Scope:** Finalize `do_wear()` ROM parity (P1-7), then audit `do_remove()`, consumables/special-object commands, and close `mob_prog`/`mob_cmds` edge cases (P1-8). Three subagents dispatched in parallel after the in-flight `do_wear()` work landed.

## What Shipped

### `do_wear()` — replace / multi-slot / two-hand finalization (P1-7)
- Surfaced ROM `"You can't remove $p."` message when an `ITEM_NOREMOVE` item blocks a replacement (`mud/commands/equipment.py`).
- Added `ch.size < SIZE_LARGE` guard on the shield-vs-two-hand check in `do_wear`, mirroring `src/act_obj.c:1603`.
- `do_wield` now skips strength and two-hand-vs-shield checks for NPCs (`IS_NPC` short-circuit at `src/act_obj.c:1623, 1631`) and respects `SIZE_LARGE` bypass.
- Replace path returns the can't-remove message instead of an empty string for both wear and hold flows.
- Upstream bug fixed: `Object` instances built directly (test fixtures, future OLC paths) didn't inherit `extra_flags`/`wear_flags` from their prototype, so `ITEM_NOREMOVE`/`ITEM_NODROP` etc. were silently dropped. Added `__post_init__` sync in `mud/models/object.py`.
- 7 new integration tests in `tests/integration/test_equipment_system.py`: NOREMOVE-blocked replace, NECK & WRIST multi-slot replace, all-NOREMOVE multi-slot rejection ("You already wear two rings."), `wear all` non-replace semantics, `SIZE_LARGE` bypass, NPC bypass for strength + two-hand checks. **Suite: 26 pass / 1 ROM-non-parity skip.**

### `do_remove()` parity audit (P1-7) — subagent
- Line-by-line vs `src/act_obj.c:1740-1763` and `remove_obj` at `src/act_obj.c:1372-1392`.
- Gap fixed: ROM emits a TO_ROOM `"$n stops using $p."` broadcast in addition to the TO_CHAR reply; Python now mirrors both via a `_perform_remove()` helper using `unequip_char` + `act_format` + `broadcast_room`.
- `wear_loc` reset to `WEAR_NONE` confirmed via `unequip_char`.
- `remove all` retained as a documented Python convenience extension (skips NOREMOVE items).
- New file `tests/integration/test_remove_command.py`: **6 pass.** Covers happy-path TO_CHAR+TO_ROOM, NOREMOVE block, no-args, item-not-worn, AC bonus revert, `remove all` skipping NOREMOVE.

### Consumables & special-object commands (P1-7) — subagent
- New audit doc `docs/parity/ACT_OBJ_C_CONSUMABLES_AUDIT.md` per command.
- Findings: all eight commands (`do_eat`, `do_drink`, `do_quaff`, `do_recite`, `do_brandish`, `do_zap`, `do_pour`, `do_fill`) are wired in `dispatcher.py`, but `do_recite`/`do_brandish`/`do_zap` raise at runtime (`ItemType.ITEM_STAFF`/`ITEM_WAND` undefined; missing `find_char_in_room` / `find_obj_in_room` / `SkillTarget` imports). `do_eat`/`do_drink` ignore `Character.condition[]` (DRUNK/FULL/THIRST/HUNGER) and substitute a non-ROM dict, omit the `COND_FULL > 40/45` gates, and apply non-canonical poison affects. `do_pour` reads `target_char.equipped` instead of `equipment` so pour-into-character never resolves.
- New file `tests/integration/test_consumables.py`: **13 pass / 7 skip** (skips point at the audit doc's documented gaps for unimplemented spell-cast paths).

### `mob_prog.c` + `mob_cmds.c` edge cases (P1-8) — subagent
- Verified `mpat`, `mptransfer`, and `mppurge` parity vs `src/mob_cmds.c`. Variable substitution ($i, $I, $n, $N, $t, $T, $e/$E, $m/$M, $s/$S, $r/$R, $p) exercised in a single mobprog snippet.
- New file `tests/integration/test_mobprog_edge_cases.py`: **7 pass.**
- Tracker P1-8 updated: 72% → 85%.

## Tracker

`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — P1-7 `do_wear()` and `do_remove()` lines flipped to ✅ with notes; consumables status reflects the new audit doc; P1-8 mob_prog edge-case section rewritten.

## Test deltas

| File | Pass | Skip | Notes |
| --- | --- | --- | --- |
| `tests/integration/test_equipment_system.py` | 26 | 1 | +7 new tests this session |
| `tests/integration/test_remove_command.py` | 6 | 0 | new file |
| `tests/integration/test_consumables.py` | 13 | 7 | new file; skips link to audit doc |
| `tests/integration/test_mobprog_edge_cases.py` | 7 | 0 | new file |
| **Net additions** | **+33** | **+7** | |

## Regression check

Full suite: **3276 pass / 62 fail / 18 skip / 96 warnings.**

The 62 failures are **pre-existing on this branch** before any of this session's work. Verified by stashing `mud/models/object.py` (the only deep-runtime change touched this session) and re-running the failing files: identical 22-fail count in the sampled subset (`test_door_portal_commands.py`, `test_combat_death.py`, `test_commands.py`, `test_encumbrance.py`). None of the failures touch `do_wear`/`do_remove`/consumables/mobprog code paths exercised here. Triaging the pre-existing failures is out of scope for this batch.

## Files touched (committable)

- `mud/commands/equipment.py` — do_wear/do_wield gap fixes
- `mud/models/object.py` — `Object.__post_init__` proto-sync
- `mud/commands/obj_manipulation.py` — `do_remove` TO_ROOM broadcast helper
- `mud/mob_cmds.py` — mpat/mptransfer/mppurge parity touch-ups (subagent)
- `mud/commands/consumption.py` — minor consumable touch-ups (subagent; verify scope before commit)
- `tests/integration/test_equipment_system.py` — +7 tests
- `tests/integration/test_remove_command.py` — new
- `tests/integration/test_consumables.py` — new
- `tests/integration/test_mobprog_edge_cases.py` — new
- `docs/parity/ACT_OBJ_C_CONSUMABLES_AUDIT.md` — new
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — P1-7 / P1-8 updates

## Recommended next steps

1. **Triage the 62 pre-existing failures** — they predate this batch but are noisy. Likely cluster around door/portal exit-info flags, scan command output, encumbrance message wording, and corpse-loot ownership. Worth a dedicated cleanup pass.
2. **Implement consumable spell-cast wiring** — fix the `ITEM_STAFF`/`ITEM_WAND` enum gap and `SkillTarget` import, then unwind the 7 skipped consumable tests one by one.
3. **`do_eat`/`do_drink` condition refactor** — port the canonical `Character.condition[]` array (DRUNK/FULL/THIRST/HUNGER) and remove the non-ROM dict.
4. **mob_prog recursion-limit edge cases** — last 15% before P1-8 hits 100%.
