# Session Summary — 2026-05-29 — FINDING-009 combat-tick round fully resolved (FIGHT-021..026)

## Scope

Continued the differential-harness-driven combat parity work. The
`combat_melee_rounds` scenario's first divergence sat at step 5 (`__tick` /
`violence_update`), root-caused into **four facets**. This session closed all
four on `master` (facet 1 via FIGHT-021/022 earlier in the session; then the
facet-3 master gap-closer, facet 2, and facet 4), plus a prerequisite crash
(FIGHT-026) that facet 3's reorder exposed. The differential was then re-run
end-to-end: **step 5 now converges on both engines**, the first divergence
advanced to **step 6**, and the new round-2 divergence is filed as FINDING-010.

## Outcomes

### `FIGHT-026` — ✅ FIXED (master 2.11.11, `850662b5`)

- **Python**: `mud/commands/combat.py` `do_dirt`/`do_trip`/`do_disarm`
- **ROM C**: `src/fight.c` do_dirt/do_trip/do_disarm (NPC `OFF_` gate; `get_curr_stat(STAT_DEX)`)
- **Gap**: NPC offensive-skill commands crashed when `mob_hit` dispatched them — `do_dirt`/`do_trip`/`do_disarm` read `char.skills.get(...)` (no `skills` on `MobInstance` → `AttributeError`); `do_trip` also `IndexError`d on the empty-list `perm_stat` default. Latent FIGHT-022 fallout, surfaced by FIGHT-024's reorder (mayor #3143 OFF_TRIP rolled into `do_trip`).
- **Fix**: NPC `OFF_`-flag gate (mirror `do_kick`/`do_berserk`, `learned=100`); `do_trip` DEX via canonical `get_curr_stat(Stat.DEX)`; added `_npc_off_flags` helper.
- **Tests**: `tests/integration/test_fight_026_npc_offensive_skill_no_crash.py` (3). Closes the crash only — flagged-mob `do_X` RNG fidelity still unverified (filed).

### `FIGHT-024` — ✅ FIXED (master 2.11.12, `863f8734`) — FINDING-009 facet 3

- **Python**: `mud/game_loop.py:violence_tick`
- **ROM C**: `src/fight.c:76` `violence_update` (head-first `char_list`); `src/db.c:2256-2257`, `src/nanny.c:757-758` (new chars prepend)
- **Gap**: `violence_tick` walked `character_registry` forward — the reverse of ROM's swing order; the shared combat RNG stream was consumed in the wrong order.
- **Fix**: iterate `list(reversed(character_registry))` (snapshot mirrors ROM's `ch_next` guard).
- **Tests**: `tests/integration/test_fight_024_violence_tick_order.py` (1).

### `FIGHT-023` — ✅ FIXED (master 2.11.13, `027eee0f`) — FINDING-009 facet 2

- **Python**: `mud/spawning/templates.py:_resolve_damage_type` / `from_prototype`
- **ROM C**: `src/db2.c:270`, `src/handler.c:165` (`attack_lookup`); `src/db.c:2086-2099`; `src/fight.c:431,2176`
- **Gap**: `MobInstance.dam_type` stored a DamageType *class*, but `engine.py` reads it as an attack_table *index* — the drunk #3064 rendered "slice" (index 1) not "beating" (index 13). Random default assigned class values `3/1/2` where ROM assigns indices `3/7/11`.
- **Fix**: `_resolve_damage_type` returns the attack-table index (via `attack_lookup`, dropping the DamageType-name fallback that could suppress ROM's `number_range(1,3)` default roll); random default → `3/7/11`. Class derived at hit time via `attack_damage_type(index)`, so the drunk now resolves DAM_BASH (was DAM_SLASH) — correct noun + AC-index/THAC0/RIV.
- **Tests**: `tests/integration/test_fight_023_mob_dam_type_attack_index.py` (2); re-baselined 2 `test_spawning.py` assertions (class → index 7).

### `FIGHT-025` — ✅ FIXED (master 2.11.14, `b8878785`) — FINDING-009 facet 4

- **Python**: `mud/combat/messages.py:render_for` / `_capitalize_act`
- **ROM C**: `src/comm.c:2373-2379` `act_new` first-char capitalization (colour-code-aware)
- **Gap**: the combat act() render chokepoint never capitalized — NPC swings rendered "the drunk's ..." vs ROM "The drunk's ...".
- **Fix**: `render_for` applies `_capitalize_act` (index 2 after a leading `{X`, else index 0). Scoped to the combat chokepoint; `broadcast_room`/`act_format` filed as ACT-CAP-001.
- **Tests**: `tests/integration/test_fight_025_act_capitalization.py` (3); hardened a pre-existing xdist-flaky `test_enhanced_damage_checks_improve` (pinned `number_bits`).

### FINDING-009 — ✅ RESOLVED; differential advanced step 5 → step 6

- `pytest tests/test_differential_smoke.py -k combat_melee` (worktree, after merging master): **step 5 converges on both engines**. First divergence now at step 6 (round-2 damage severity: C "scratches" ≤5% vs py "hits" ≤15%).
- Filed **FINDING-010** (round-2 damage amount — root cause unknown; rule out regression from FIGHT-023/021/022 first) on the diff-harness branch (`9bc1a489`).

## Files Modified

- `mud/commands/combat.py` — FIGHT-026 NPC-safe do_dirt/do_trip/do_disarm + `_npc_off_flags`
- `mud/game_loop.py` — FIGHT-024 `violence_tick` reversed iteration
- `mud/spawning/templates.py` — FIGHT-023 dam_type as attack-table index
- `mud/combat/messages.py` — FIGHT-025 `_capitalize_act` in `render_for`
- `tests/integration/test_fight_023..026_*.py` — new regression tests
- `tests/test_spawning.py`, `tests/test_combat_skills.py`, `tests/integration/test_group_combat.py` — re-baselines / brittleness hardening
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-023/024/025/026 rows ✅ + follow-ups (SHOP-PET-001, ACT-CAP-001, NPC do_X RNG fidelity)
- `CHANGELOG.md` — `[2.11.11]`..`[2.11.14]`
- `pyproject.toml` — 2.11.10 → 2.11.14
- (diff-harness branch) `tools/diff_harness/FINDINGS.md`, `tests/test_differential_smoke.py` — FINDING-009 resolved, FINDING-010 filed

## Test Status

- Full suite (master, post-FIGHT-023 re-baseline): **4942 passed, 4 skipped** (159s).
- Post-FIGHT-025 re-run (un-hardened test): **4945 passed** (confirmed the lone failure was a non-deterministic xdist flake, since hardened).
- Differential smoke (worktree): movement_get_drop PASS, combat_melee_rounds XFAIL under FINDING-010.
- `ruff check` on all touched files clean (pre-existing CI-tolerated debt in `templates.py` unchanged).

## Next Steps

- **FINDING-010** (combat round-2 damage severity): probe the per-round draw *sequence* + damage components (dice, damroll, STR app, RIV, **drunk wait-state between rounds**) for both engines at step 6. Draw counts diverge by round 2 → facet-1/wait-state residual (rule out FIGHT-021/022/023 regression first); draws match but damage differs → formula bug. File as FIGHT-NNN once isolated.
- **Outstanding follow-ups** (filed in `docs/parity/FIGHT_C_AUDIT.md`): `SHOP-PET-001` (pet `dam_type` bypasses `from_prototype`), `ACT-CAP-001` (non-combat act() capitalization at `broadcast_room`/`act_format`), NPC `do_X` per-command RNG-draw fidelity for flagged mobs.
