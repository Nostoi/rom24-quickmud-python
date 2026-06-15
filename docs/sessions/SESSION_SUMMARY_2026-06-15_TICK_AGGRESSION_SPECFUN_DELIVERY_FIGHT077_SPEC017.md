# Session Summary — 2026-06-15 — Tick aggression + spec-fun delivery (FIGHT-077 + SPEC-017)

## Scope

A player reported two tick-driven symptoms on the web client
(`../quickmud-web-client`): (1) aggressive monsters were not proactively
attacking, and (2) friendly mobs (the cage-room adept) were not proactively
casting healing spells on ticks. They explicitly suspected **more** tick-based
problems than the two named, so the session also ran a broad sweep of the tick
path rather than stopping at the two symptoms.

Root-cause analysis found exactly **two distinct** live tick bugs, both now
fixed: FIGHT-077 (a fabricated `is_safe` NPC level gate suppressing aggression)
and SPEC-017 (spec-fun room flavor delivered mailbox-only, invisible to idle
connected players at tick time). The broader sweep confirmed no additional live
tick bugs — other tick-time mailbox-only deliveries were already closed by
XP-DELIVERY-001 and the INV-001 SINGLE-DELIVERY sweep, and combat weapon-effects
are single-delivered via `_push_message`.

## Outcomes

### `FIGHT-077` — ✅ FIXED (commit 5a93cec7)

- **Python**: `mud/combat/safety.py:is_safe` (NPC-attacking-PC branch).
- **ROM C**: `src/fight.c:1075-1093` ("NPC doing the killing") — only a safe-room
  check and a charmed-pet-owner check; **no** level-difference gate.
  `apply_damage` re-checks `is_safe` at entry (`src/fight.c:731`) and returns
  `""` when safe.
- **Gap**: FIGHT-077 — `is_safe` carried a fabricated
  `if victim_level < char_level - 10: return True` gate with no ROM basis, so
  any mob more than 10 levels above a PC silently refused to aggress (no damage,
  no `fighting` set). The missed level-gate facet of INV-050 (silent `is_safe`
  over-block); the faithful mirror `_kill_safety_message` in
  `mud/commands/combat.py` already correctly omitted any level gate.
- **Fix**: deleted the fabricated gate; the branch now matches ROM's two guards.
- **Tests**: `tests/integration/test_fight077_is_safe_no_npc_level_gate.py`
  (verified failing pre-fix). Live-verified: a level-13 mob now kills a level-1
  PC (the reproduced Eddol vs Cave Dweller case).

### `SPEC-017` — ✅ FIXED (commit c47d550e)

- **Python**: `mud/spec_funs.py:_append_message` — the single sink for every
  spec-fun room message (adept cast, mayor, janitor, fido, thief, poison,
  breath).
- **ROM C**: `src/comm.c:act` — writes spec-fun flavor straight to each
  recipient's descriptor via `write_to_buffer` (synchronous, single delivery).
- **Gap**: SPEC-017 — `_append_message` appended only to the `char.messages`
  mailbox and never the socket. It was the **last** mailbox-only delivery helper
  missed by the INV-001 SINGLE-DELIVERY sweep (its identical `mud/mob_cmds.py`
  twin was migrated in 2.12.71). For a *connected* PC the line only surfaced
  after the player's NEXT command (the connection read loop drains the mailbox),
  so an idle web-client player watching the cage-room adept never saw the casting
  announcement on a game tick — the user-visible "friendly mobs aren't casting"
  symptom. The adept *was* casting (effect messages reached the socket via
  `push_message`); only the flavor line was on the wrong channel. INV-001
  wrong-channel cousin.
- **Fix**: route `_append_message` through the loop-aware chokepoint
  `mud.utils.messaging.push_message` (async socket for connected PCs, mailbox
  fallback for tests/disconnected). Fixes all spec-fun flavor consistently.
- **Tests**: `tests/integration/test_spec017_delivery_channel.py` (3 tests;
  2/3 verified failing pre-fix).

## Broader tick-path sweep (the "more problems" suspicion)

- `mud/game_loop.py:async_game_loop` logs per-tick exceptions
  (`traceback.print_exc()` + backoff) — it does **not** silently swallow errors.
- Other tick-time mailbox-only deliveries already closed: death/XP chain
  (XP-DELIVERY-001), room broadcasts / say / position changes (INV-001 sweep).
- `mud/combat/engine.py:process_weapon_special_attacks` does both `_push_message`
  and `messages.append` + return, but every `multi_hit` caller discards the
  return — single-delivered in practice. **Vestigial, not a live bug** (latent
  INV-001 footgun; noted below as optional cleanup).

Conclusion: exactly two distinct tick-based root causes, both fixed; no
additional live tick bugs found.

## Files Modified

- `mud/combat/safety.py` — FIGHT-077: removed fabricated NPC level gate.
- `mud/spec_funs.py` — SPEC-017: `_append_message` → `push_message`.
- `tests/integration/test_fight077_is_safe_no_npc_level_gate.py` — new.
- `tests/integration/test_spec017_delivery_channel.py` — new (3 tests).
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-077 row ✅ FIXED.
- `docs/parity/SPECIAL_C_AUDIT.md` — SPEC-017 row ✅ FIXED.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 "Touched by" trail
  (`spec_funs.py:_append_message`, SPEC-017).
- `CHANGELOG.md` — FIGHT-077 + SPEC-017 Fixed entries.
- `pyproject.toml` — 2.14.114 → 2.14.115.

## Test Status

- `tests/integration/test_fight077_is_safe_no_npc_level_gate.py` — passing.
- `tests/integration/test_spec017_delivery_channel.py` — 3/3 passing.
- Full suite: 5812 passed, 4 skipped (199.62s).
- `ruff check .` — clean (pre-commit hooks passed on both commits).

## Next Steps

Per-file audit tracker remains exhausted (43/43; P0/P1/P2 100%, P3 75% + 3 N/A)
— cross-file invariants / divergence-class sweep stays the active pass. Open
follow-ups (carried + new):

- **Vestigial dual-channel in `process_weapon_special_attacks` (new, optional)**
  — `mud/combat/engine.py` builds both `_push_message` and a `messages.append`
  return list; all `multi_hit` callers discard the return, so it is not a live
  bug, but it is a latent INV-001 footgun if a future caller ever consumes the
  return. Low-priority cleanup, not yet filed as a stable ID.
- **Eddol data cleanup (needs user confirmation)** — the existing corrupt
  `Eddol` DB row is forward-only unaffected; deleting it is destructive.
- **DELETE-002 🔄 OPEN** — `do_delete` lacks ROM's wiznet self-deletion
  broadcast (`src/act_comm.c`). Local divergence, low priority.
- **STEAL-015 🔄 OPEN** — steal skill-handler `skills/handlers.py:steal` has no
  `is_safe` gate; converge onto `_kill_safety_message`.
- **INV-050 bool-retirement** — gated on the `is_safe_spell`-vs-ROM audit
  (`safety.py:is_safe_spell` vs `src/fight.c:1126-1218`); message-half done,
  FIGHT-077 closed the missed level-gate facet.
- **`mud/entrypoint.py`** dead code (`prompt_account_creation` / `prompt_login`,
  no callers) — candidate for a hygiene-pass removal.
