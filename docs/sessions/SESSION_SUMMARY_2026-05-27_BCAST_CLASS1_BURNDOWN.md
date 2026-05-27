# Session Summary — 2026-05-27 — BCAST Class 1 burn-down (2.9.62)

## Headline

Fourth session of 2026-05-27. Drove the META Class 1 BROADCAST_COVERAGE burn-down to **substantial completion**: closed the 3 confirmed real gaps (BCAST-034 pick, BCAST-035 purge, BCAST-030 bash), closed the CLONE-001 pre-existing bug that was blocking BCAST-002 mob branch, closed BCAST-002 mob branch on top, then ran a per-row probe pass over the 16 remaining ⚠️/❌ rows and reclassified 13 as ✅ COVERED (helper-transitivity false positives) while narrowing 3 to ⚠️ Partial with new stable gap IDs (GROUP-001, ORDER-001, STEAL-001).

Cumulative Class 1 status after this session: **every row in BROADCAST_COVERAGE.md is now ✅ FIXED, ✅ COVERED, or ⚠️ Partial-blocked-by-stable-ID.** The only ⚠️ rows remaining (BCAST-009/017/038) each point at a documented Blocked-rows entry with a known fix shape. The bulk burn-down phase is done; what remains is targeted gap-closer work on the three new IDs.

## Commits (6 on master this session — 6 ahead of `origin/master` total)

| SHA | Type | Content |
|-----|------|---------|
| `afb0acb` | feat(parity) | BCAST-034 — `do_pick` emits ROM TO_ROOM on all 3 paths (portal, container, door) with `$d` resolved via `_door_keyword`. |
| `e5259a8` | feat(parity) | BCAST-035 — `do_purge` emits ROM TO_ROOM (room-purge) and TO_NOTVICT (PC-disintegrate, NPC-purge) via new local `_notvict_broadcast` helper supporting two-actor exclude. |
| `bd64ad4` | fix(parity) | BCAST-030 — `bash` skill handler emits all 4 ROM TO_VICT/TO_NOTVICT acts (success + failure paths) with `$s`/`$m` pronoun substitution via new `_objective_pronoun` helper + `_to_vict_send` / `_notvict_broadcast` delivery helpers. |
| `aa08af8` | fix(parity) | CLONE-001 — `do_clone` mob branch imports valid LEVEL_ constants. Added `LEVEL_AVATAR=52`, `LEVEL_DEMI=54`, `LEVEL_IMMORTAL_TIER=55`, `LEVEL_GOD=56` (preserving `LEVEL_IMMORTAL=52` threshold). Fixed gate to match ROM ladder including missing `IS_TRUSTED(AVATAR)` floor. |
| `ea168a5` | feat(parity) | BCAST-002 (mob branch) — `do_clone` mob branch emits TO_ROOM `$n has created $N.` after placement, unblocked by CLONE-001. |
| `be7eb60` | docs(parity) | Class A burn-down probe — 13 ✅ COVERED reclassifications + 3 new gap IDs filed (GROUP-001, ORDER-001, STEAL-001) in BROADCAST_COVERAGE.md Blocked rows. |
| (pending) | chore(parity) | Session handoff — 2.9.62 version, CHANGELOG section, summary, STATUS. |

## Outcomes

### `BCAST-034` (`do_pick`) — ✅ FIXED

- **Python**: `mud/commands/doors.py:do_pick`
- **ROM C**: `src/act_move.c:907, 945, 981` — 3 TO_ROOM acts (portal, container, door)
- **Fix**: `broadcast_room(room, f"{actor_name} picks the lock on $obj.", exclude=char)` for portal/container; `broadcast_room(room, f"{actor_name} picks the {_door_keyword(pexit)}.", exclude=char)` for door (`$d` substitution via existing `_door_keyword` helper).
- **Tests**: `tests/integration/test_pick_broadcasts.py` (2/2).

### `BCAST-035` (`do_purge`) — ✅ FIXED

- **Python**: `mud/commands/imm_load.py:do_purge`
- **ROM C**: `src/act_wiz.c:2605` (room-purge TO_ROOM), `:2633` (PC-disintegrate TO_NOTVICT), `:2645` (NPC-purge TO_NOTVICT)
- **Fix**: `broadcast_room` for room-purge `$n purges the room!`; new local `_notvict_broadcast` helper for the two TO_NOTVICT paths. The helper mirrors `broadcast_room` but supports a two-actor exclude set since ROM TO_NOTVICT skips both the actor and the about-to-be-extracted victim.
- **Tests**: `tests/integration/test_purge_broadcasts.py` (2/2).

### `BCAST-030` (`bash` skill) — ✅ FIXED

- **Python**: `mud/skills/handlers.py:bash`
- **ROM C**: `src/fight.c:2459-2465` (success), `:2478-2481` (failure) — 4 non-TO_CHAR acts total
- **Fix**: Added all 4 acts:
  - success TO_VICT `$n sends you sprawling with a powerful bash!`
  - success TO_NOTVICT `$n sends $N sprawling with a powerful bash.`
  - failure TO_NOTVICT `$n falls flat on $s face.`
  - failure TO_VICT `You evade $n's bash, causing $m to fall flat on $s face.`
- **New helpers**: `_objective_pronoun(char) → him/her/it` (for `$m`), `_to_vict_send(victim, msg)` (single-recipient delivery), `_notvict_broadcast(room, actor, victim, msg)` (two-actor exclude — same shape as the imm_load.py helper). Reused existing `_possessive_pronoun` for `$s`.
- **Tests**: `tests/integration/test_bash_broadcasts.py` (2/2 — success path + failure path with female-attacker pronoun verification).

### `CLONE-001` — ✅ FIXED (Option 2 path)

- **Python**: `mud/commands/imm_search.py:do_clone` mob branch trust gate; `mud/models/constants.py`
- **ROM C**: `src/act_wiz.c:2424-2429`; `merc.h:162-170`
- **Bug**: gate imported `LEVEL_AVATAR`/`LEVEL_DEMI`/`LEVEL_GOD` from `mud.models.constants` where only `LEVEL_IMMORTAL=52` and `LEVEL_ANGEL=53` existed → every `clone <mob>` call ImportError'd before reaching the spawn or broadcast.
- **Fix (Option 2 — low blast radius)**: added `LEVEL_AVATAR = 52`, `LEVEL_DEMI = 54`, `LEVEL_IMMORTAL_TIER = 55`, `LEVEL_GOD = 56` to constants.py without touching the existing `LEVEL_IMMORTAL = 52` threshold (which is semantically the "any immortal" check used by `IS_IMMORTAL`, distinct from ROM's `IMMORTAL=55` trust tier). Updated do_clone gate to use `LEVEL_IMMORTAL_TIER` for the `mob_level > 10` rung (ROM gates on the tier, not the threshold), use `LEVEL_ANGEL` for `mob_level > 0` (was incorrectly `LEVEL_AVATAR`), and add the unconditional `IS_TRUSTED(AVATAR)` floor that ROM enforces and Python had been silently missing.
- **Tests**: `tests/integration/test_act_wiz_command_parity.py::test_clone_mob_success_no_import_error_and_places_clone`.
- **Unblocks**: BCAST-002 mob branch (closed immediately below).

### `BCAST-002` (mob branch) — ✅ FIXED

- **Python**: `mud/commands/imm_search.py:do_clone` mob branch (after `room.people.append(clone)`)
- **ROM C**: `src/act_wiz.c:2450` — `act("$n has created $N.", ch, NULL, clone, TO_ROOM)`
- **Fix**: `broadcast_room(room, f"{actor_name} has created {clone_short}.", exclude=char)` with the same `short_descr` → `prototype.short_descr` → `name` fallback chain as BCAST-014/015.
- **Tests**: `tests/integration/test_clone_broadcasts.py::test_clone_mob_emits_to_room_broadcast`.
- **Completes BCAST-002** — both obj and mob branches now ROM-faithful.

### Class A burn-down probe — 13 ✅ COVERED, 3 ⚠️ Partial with new gap IDs (no code change)

Sonnet subagent probe pass over the 16 remaining Class 1 BCAST rows. Verdicts:

**Reclassified to ✅ COVERED** (helper-transitivity false positives, same pattern as the BCAST-001/004/005/007/008/019/020/026/029 collapses):

| Row | Command | Helper / explanation |
|-----|---------|----------------------|
| BCAST-006 | `enter` | `move_character_through_portal` at `mud/world/movement.py:470` emits all 5 ROM acts via `broadcast_room` |
| BCAST-010 | `gtell` | per-member `send_to_char` loop in `group_commands.py:331` (async real-time) |
| BCAST-021 | `rest` | local `_broadcast` helper at `position.py:91` wraps `broadcast_room`; called 6× across position×furniture branches |
| BCAST-022 | `sit` | same `_broadcast` helper, 6 call sites including ROM bug-faithful `$n wakes and sits at $p` on SIT_ON |
| BCAST-023 | `sleep` | same `_broadcast` helper, no-furniture + furniture branches |
| BCAST-024 | `stand` | same `_broadcast` helper, 4 call sites covering all SLEEPING/RESTING/SITTING × furniture variants |
| BCAST-028 | `value` | ROM has no TO_ROOM acts; Python delivers all TO_VICT keeper→customer responses via `_keeper_says()` returned string |
| BCAST-031 | `buy` | `room.broadcast` for `$n buys $p[N].` (shop.py:831); pet-shop branch uses `current_room.broadcast` (line 631) |
| BCAST-032 | `force` | `_send_to_char(vch/victim, …)` at 4 branch sites in imm_commands.py; ROM has no TO_ROOM |
| BCAST-033 | `give` | `_broadcast_to_room_observers` + `send_to_char` task for both item-give and money-give paths (covered by INV-013 single-delivery) |
| BCAST-036 | `recall` | 3× `room.broadcast` covering departure/disappear/arrive (session.py:356, 399, 411) |
| BCAST-037 | `sell` | `room.broadcast` for `$n sells $p.` (shop.py:941) |
| BCAST-039 | `transfer` | 2× `_act_room` + 1× `_send_to_char` (imm_commands.py:273-283) |

**Narrowed to ⚠️ Partial with new gap IDs** (filed durably in BROADCAST_COVERAGE.md Blocked rows):

| Row | New gap ID | Real divergence |
|-----|-----------|----------------|
| BCAST-009 | **GROUP-001** | `do_group` TO_VICT/TO_NOTVICT delivered via `victim.messages.append` and per-bystander `.messages.append` loops only — never through `send_to_char` or `broadcast_room`. Players on live sockets see nothing. Adjacent: `$N isn't following you.` returned as plain string where ROM uses `act_new(..., TO_CHAR, POS_SLEEPING)`. |
| BCAST-017 | **ORDER-001** | `do_order` broadcast delivery is real-time correct, but the message is manually formatted as `f"{char.name} orders you to '…'"` rather than via `act()` — bypasses `can_see_character` visibility gating so wiz-invis orderers reveal themselves. Adjacent: ROM checks `arg2` (second word) for the "delete"/"mob" guard; Python checks word 0. |
| BCAST-038 | **STEAL-001** | `_steal_failure` TO_VICT (`$n tried to steal from you.`) and TO_NOTVICT (`$n tried to steal from $N.`) at `thief_skills.py:187, 192` delivered via `.messages` only — connected players see nothing on a failed steal. Success item-path is correct (ROM is TO_CHAR-only). |

All three follow the same fix shape used for BCAST-035 / BCAST-030 in this session: replace `.messages`-only delivery with `broadcast_room` (or a two-actor exclude helper like `_notvict_broadcast`) plus an explicit `send_to_char` for TO_VICT.

## Files Modified

- `mud/commands/doors.py` — BCAST-034 (3 TO_ROOM emits in `do_pick`).
- `mud/commands/imm_load.py` — BCAST-035 (3 emits in `do_purge`); added module-local `_notvict_broadcast` helper.
- `mud/skills/handlers.py` — BCAST-030 (4 emits in `bash`); added `_objective_pronoun`, `_to_vict_send`, `_notvict_broadcast` helpers.
- `mud/commands/imm_search.py` — CLONE-001 (trust-gate constants + ladder); BCAST-002 mob branch TO_ROOM emit.
- `mud/models/constants.py` — added `LEVEL_AVATAR`, `LEVEL_DEMI`, `LEVEL_IMMORTAL_TIER`, `LEVEL_GOD` (preserving existing `LEVEL_IMMORTAL` threshold).
- `tests/integration/test_pick_broadcasts.py` (new) — 2 BCAST-034 tests.
- `tests/integration/test_purge_broadcasts.py` (new) — 2 BCAST-035 tests.
- `tests/integration/test_bash_broadcasts.py` (new) — 2 BCAST-030 tests (success path + failure with female-attacker pronouns).
- `tests/integration/test_clone_broadcasts.py` — added BCAST-002 mob-branch test.
- `tests/integration/test_act_wiz_command_parity.py` — added CLONE-001 success-path test.
- `docs/parity/audits/BROADCAST_COVERAGE.md` — row flips: BCAST-002/030/034/035 → ✅ FIXED; BCAST-006/010/021/022/023/024/028/031/032/033/036/037/039 → ✅ COVERED; BCAST-009/017/038 → ⚠️ Partial with new gap IDs. CLONE-001 status → ✅ FIXED. New Blocked-rows entries: GROUP-001, ORDER-001, STEAL-001.
- `CHANGELOG.md` — new 2.9.62 section (Added BCAST-030/034/035/002-mob; Fixed CLONE-001; Changed bulk Class A reclassification + 3 new gap IDs).
- `pyproject.toml` — 2.9.61 → 2.9.62.
- `docs/sessions/SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_BURNDOWN.md` (new).
- `docs/sessions/SESSION_STATUS.md` — refreshed.

## Test Status

- `pytest tests/integration/test_pick_broadcasts.py` — 2/2 passing.
- `pytest tests/integration/test_purge_broadcasts.py` — 2/2 passing.
- `pytest tests/integration/test_bash_broadcasts.py` — 2/2 passing.
- `pytest tests/integration/test_clone_broadcasts.py` — 2/2 passing (object + mob branch).
- `pytest tests/integration/test_act_wiz_command_parity.py` — 114/114 passing.
- `pytest tests/test_skill_combat_rom_parity.py` — 104/104 passing (regression check on `bash` skill).
- **Full integration suite**: `pytest tests/integration/ -q --timeout=60` — **2297 passed + 3 skipped in 77s** (up from 2289 at 2.9.61 close; +8 new tests this session).

## Next Steps

1. **Push approval required** — 6 commits ahead of `origin/master`, all for 2.9.62 (BCAST-034, BCAST-035, BCAST-030, CLONE-001, BCAST-002 mob, Class A probe doc).
2. **GROUP-001 + STEAL-001 closure** — both share the `.messages` → `broadcast_room`/`send_to_char` fix shape used for BCAST-035 in this session. Pair them as two consecutive gap-closer commits; should be quick (~20 min each). Closes BCAST-009 + BCAST-038 once landed.
3. **ORDER-001 closure** — needs an `act()`-equivalent helper that does `can_see_character` gating, then route the order message through it. Higher value than just the visibility gate — establishes the pattern for future "manual format" → `act()`-style migrations. Also fixes the wrong word-position guard. Closes BCAST-017.
4. **After the three Blocked-row closures, BROADCAST_COVERAGE.md is fully ✅** — all 209 rows either FIXED / COVERED / not-applicable. Class 1 META audit is complete; move on to Class 2 ARITHMETIC_BOUNDARY (or another META class).
5. **INV-027 promotion** (ACT-INVIS-TRUST-GATE, from BCAST-029 probe) — introduce `_can_witness(actor, witness)`, thread through `_act_room` / `broadcast_room`, regression test. ORDER-001 in step 3 is a natural lead-in since it exercises the same gating gap on a different surface.
6. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` — still unresolved.
7. **GitNexus reindex** still stale (last `069f17f`, now ~30+ commits behind). FTS index reported read-only/broken throughout this session. Run `npx gitnexus analyze --skip-agents-md` before next probe-heavy session.
8. **Worktree hygiene** — 5 locked worktrees still pending in `.claude/worktrees/`.
9. **Remaining META classes** (after Class 1 finishes): Class 2 ARITHMETIC_BOUNDARY, Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION, Class 5 LIFECYCLE_STAGING.
