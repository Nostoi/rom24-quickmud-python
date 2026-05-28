# Session Summary — 2026-05-28 — FIGHT-017 envenom level source + per-hit poison weakening (2.9.89)

## Scope

Picked up from the FIGHT-016 session (2.9.88) with the per-file audit tracker
exhausted (no ⚠️ Partial / ❌ Not Audited rows), so the active mode is the
cross-file / remaining-documented-gap pass. `SESSION_STATUS.md` named **FIGHT-017**
as the next intended task — the temporary-envenomed-weapon half of the
WEAPON_POISON divergence that FIGHT-016 (timed STR-reducing affect) left open.
Closed it via `/rom-gap-closer` (one gap, four tests, one commit).

GitNexus MCP query path was read-only all session (`Cannot execute write
operations in a read-only database`), so impact analysis used the documented
`grep` + test-suite fallback. The single production caller of
`process_weapon_special_attacks` is `engine.py` `apply_damage` (LOW risk). The
CLI `npx gitnexus analyze --skip-agents-md` **did** succeed at end of session
(21.8s, 41,110 nodes) — the read-only state affected only the live MCP query
connection, not the rebuild, so the graph is now fresh.

## Outcomes

### `FIGHT-017` — ✅ FIXED

- **Python**: `mud/combat/engine.py:1561-1635` (`process_weapon_special_attacks`, WEAPON_POISON branch)
- **ROM C**: `src/fight.c:605-608, 627-636`
- **Gap**: ROM derives the poison `level` from a **temporary** envenom affect on
  the weapon when present — `affect_find(wield->affected, gsn_poison)` →
  `poison->level`, else `wield->level` — and after applying the venom weakens a
  temporary poison **per hit**: `poison->level = UMAX(0, poison->level - 2)`,
  `poison->duration = UMAX(0, poison->duration - 1)`, emitting `"The poison on
  $p has worn off."` to the **wielder** (TO_CHAR) when either reaches 0. Python's
  branch ignored `wield.affected` entirely (always used the weapon level) and
  never decayed an envenom.
- **Fix**: the WEAPON_POISON branch now scans `wield.affected` (guarded by
  `isinstance(..., list)` so Mock weapons in unit tests don't break) for the
  affect with `spell_name == "poison"` — the same affect `spell_poison` casts on
  an object at `handlers.py:6388-6398`. When found, `level = poison_af.level`
  (raw, no floor — a level-0 envenom must still pass `saves_spell(0, …)` and
  weaken); else `level = max(1, weapon_level)` (the ARITH-004 dead floor,
  preserved). After the save block — **outside** it, so weakening runs whether
  or not the victim saved — a present `poison_af` is decremented and the worn-off
  message is `_push_message`'d to the attacker when `level == 0 or duration == 0`.
  Permanent WEAPON_POISON weapons (no envenom affect) are unchanged.
- **Tests**: `tests/integration/test_weapon_poison_affect.py::test_fight_017_*`
  — 4 cases, all verified failing pre-fix:
  - `..._temporary_envenom_is_the_level_source` — weapon level 2 + envenom level
    40 → victim effect.level 30 / duration 20 (would be 1/1 from weapon level);
    envenom weakened 40→38, 5→4.
  - `..._weakening_happens_even_on_successful_save` — save passes, no victim
    affect, but envenom still 40→38, 5→4.
  - `..._worn_off_message_goes_to_attacker_not_victim` — level 2→0 fires the
    message to `attacker.messages`, not `victim.messages`.
  - `..._worn_off_fires_when_duration_hits_zero` — duration 1→0 (level still 8)
    fires the message (ROM `||`, not `&&`).
- **Commit**: `6b7f80d4`.

## Files Modified

- `mud/combat/engine.py` — WEAPON_POISON branch: envenom level source + per-hit weakening (FIGHT-017).
- `tests/integration/test_weapon_poison_affect.py` — `_envenom()` helper + `affected` list on `_MockWeapon`; 4 new FIGHT-017 cases.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-017 row flipped ❌ MISSING → ✅ FIXED (2.9.89); status header updated (FIGHT-016/017 both fixed).
- `CHANGELOG.md` — 2.9.89 section (FIGHT-017).
- `pyproject.toml` — 2.9.88 → 2.9.89.

## Test Status

- `tests/integration/test_weapon_poison_affect.py` — 6/6 (2 FIGHT-016 + 4 FIGHT-017).
- `tests/test_weapon_special_attacks.py` — 12/12 (Mock-weapon regression fixed via `isinstance` guard).
- Combat/weapon/fight integration slice — 124 passed, 1 skipped.
- Full suite: **4900 passed, 4 skipped, 0 failed** in 111.57s (parallel `-n auto`).
- `ruff check` on changed files — clean.

## Next Steps

1. **Remaining open ARITH (6 ❌ MISSING)** in `docs/parity/audits/ARITHMETIC_BOUNDARY.md`:
   ARITH-017/018/019 (spell-handler level floors — likely N/A like
   ARITH-020..023, verify reachability first), ARITH-114 (per-race/class stat
   ceiling — larger), ARITH-206/207 (reset arg floors — likely N/A like
   ARITH-209), ARITH-208 (template dice+bonus floor — genuinely reachable).
2. **`fight.c` remaining open**: FIGHT-004..008 (PERS position-change broadcast
   surface, `_position_change_message`) — opened 2026-05-23, still open.
3. **Push approval** — `master` is 1 commit ahead of `origin/master`
   (6b7f80d4 FIGHT-017 / 2.9.89; the 2.9.88 commits are already on origin). Not
   pushed (awaiting approval).
4. **`_wear_all` light handling** and **`CLEANUP-001`** (hex flag literals)
   carried over.
5. **GitNexus** — MCP query path read-only this session; CLI `analyze` works and
   was re-run (graph fresh). If the MCP path stays read-only next session, fix DB
   perms/lock outside the session.
