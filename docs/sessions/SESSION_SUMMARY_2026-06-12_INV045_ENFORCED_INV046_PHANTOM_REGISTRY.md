# Session Summary — 2026-06-12 — INV-045 enforced (GL-043 + HANDLER-006); INV-046 PHANTOM-REGISTRY filed

## Scope

Continuation from v2.14.14 (INV-045 ⚠️ PARTIAL, two offenders left). The session closed both —
the RNG-bearing `aggr_update` walk (GL-043) and the `get_char_world` first-match world scan
(HANDLER-006) — and flipped **INV-045 (CHAR-LIST-WALK-ORDER) to ✅ ENFORCED**: all five tick
walks plus the world scan now visit newest-first, each locked by a per-site test.

While running the mandatory `gitnexus_impact` on `get_char_world`, the disambiguation step
surfaced a SECOND Python `get_char_world` in `mud/commands/imm_commands.py` — a divergent
duplicate that scans `registry.char_list` / `registry.players`, attributes that **do not exist
on `mud/registry.py` in production**. Only tests inject them, so the act_wiz test suite passes
while every production immortal world-by-name lookup silently resolves nothing. Filed as
**INV-046 (PHANTOM-REGISTRY)** with a 17-site inventory; left ❌ OPEN for the next session.

Three commits (two gap closures + tracker docs). v2.14.14 → 2.14.16; 5626 → 5628 tests.

## Outcomes

### `GL-043` — ✅ FIXED (2.14.15, commit `0075062c`)

- **Python**: `mud/ai/aggressive.py:aggressive_update`
- **ROM C**: `src/update.c:1087-1092` (`aggr_update` walks `char_list` for the PC `wch`) +
  `src/db.c:2256-2257` / `src/nanny.c:757-758` (head-insert)
- **Gap**: the watcher walk was oldest-first — the `number_bits(1)` aggression coin
  (update.c:1107) and `number_range(0, count)` victim reservoir (update.c:1126) consumed the
  shared Mitchell-Moore stream in reversed watcher order vs C whenever ≥2 non-immortal PCs
  were live. Last RNG-bearing offender in INV-045's inventory.
- **Fix**: reversed walk + extracted-skip (`multi_hit` can extract a later watcher mid-tick;
  ROM's saved `wch_next` pointer never revisits an extracted char) — same pattern as
  GL-040/041/042.
- **Tests**: `tests/integration/test_mob_ai.py::TestAggressiveUpdateIterationOrder` (scripted
  coins `[1, 0]` with `multi_hit` stubbed: the single attack must land on the NEWEST watcher's
  aggressor; fails on a forward walk).

### `HANDLER-006` — ✅ FIXED (2.14.16, commit `d789cf28`)

- **Python**: `mud/world/char_find.py:get_char_world`
- **ROM C**: `src/handler.c:2234-2240` + the same head-insert sites
- **Gap**: INV-045 consequence class (b), first-match selection. ROM's world scan walks
  head-inserted `char_list`, so the first `is_name` match is the NEWEST same-named char and
  `2.name` counts newest→oldest; the forward registry scan inverted both (`tell guard`,
  `cast ... guard`, every `get_char_world` caller resolved the opposite instance).
- **Fix**: `for ch in reversed(character_registry)` (no snapshot needed — the scan does not
  extract).
- **Tests**: `tests/integration/test_handler006_get_char_world_newest_match.py` (two same-named
  mobs: unnumbered lookup resolves the newest, `2.name` the older).

### `INV-045` — ✅ ENFORCED (2.14.16, commit `bb67849f`)

- **Tracker**: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — CHAR-LIST-WALK-ORDER
- **Conforming sites**: `violence_tick` (FINDING-009), `obj_update` (GL-040), `char_update`
  (GL-041), `mobile_update` (GL-042), `aggressive_update` (GL-043), `get_char_world`
  (HANDLER-006) — each with a per-site iteration-order test.
- **Documented residual**: lower-stakes forward walks (broadcasts, wiznet, info scans) diverge
  only in message order; re-open a per-site gap if a scenario/golden ever observes it.

### `INV-046` — ❌ OPEN (filed, 2.14.16, commit `bb67849f`)

- **Tracker**: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — PHANTOM-REGISTRY
- **Contract**: ROM has exactly ONE live-character list; every immortal command resolves
  targets through the same `src/handler.c` lookups as the rest of the engine.
- **Violation**: 17 sites read `getattr(registry, "char_list", [])` /
  `getattr(registry, "players", {})` — attributes never set in production (`mud/registry.py`
  defines only area/mob/obj/room/shop registries). They exist only when tests inject them
  (`tests/integration/test_act_wiz_command_parity.py` ×15, `test_inv029_act_first_letter_cap.py`),
  so the suite is green while production paths scan nothing. Worst family: the duplicate
  `get_char_world`/`get_char_room` pair in `mud/commands/imm_commands.py` (substring match, no
  `can_see`, shadows the ROM-correct `mud/world/char_find.py` pair; imported by `imm_punish.py`,
  `imm_load.py`, `remaining_rom.py`) — production notell/freeze/transfer/force-by-name answer
  "They aren't here." for every live target.
- **Site inventory**: `imm_commands.py:72,80,248,380,401`, `imm_server.py:44,48,75,82,237,238`,
  `imm_search.py:258,277,363`, `imm_load.py:349`, `imm_emote.py:216`, `player_config.py:189`.
- **Fix shape**: delete the duplicate lookup pair, route callers through `mud.world.char_find`
  + `character_registry`/`descriptor_list`, rewrite the injecting tests to populate
  `character_registry`, then add a Layer-A grep-guard forbidding the phantom-attr pattern.

## Files Modified

- `mud/ai/aggressive.py` — GL-043 reversed walk + extracted-skip
- `mud/world/char_find.py` — HANDLER-006 reversed world scan
- `tests/integration/test_mob_ai.py` — +1 test class (GL-043)
- `tests/integration/test_handler006_get_char_world_newest_match.py` — new file (HANDLER-006)
- `docs/parity/UPDATE_C_AUDIT.md` — GL-043 filed + flipped ✅
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-006 filed + flipped ✅
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-045 → ✅ ENFORCED; INV-046 filed ❌ OPEN
- `CHANGELOG.md` — `[2.14.15]`, `[2.14.16]` entries
- `pyproject.toml` — 2.14.14 → 2.14.16

## Test Status

- `pytest tests/integration/test_mob_ai.py` — 17/17 passing
- `pytest tests/integration/test_handler00*.py tests/integration/test_tell_parity.py
  tests/integration/test_act_wiz_command_parity.py tests/integration/test_json_loader_parity.py`
  — 185/185 passing
- Full suite: **5628 passed, 4 skipped** (2026-06-12, post-HANDLER-006)

## Outstanding

- **INV-046 (PHANTOM-REGISTRY)** — ❌ OPEN, highest-value next target. Production immortal
  world lookups are dead code paths masked by test-injected registry attributes. Close it
  site-family by site-family, starting with the `imm_commands.py` duplicate
  `get_char_world`/`get_char_room` pair; each family is one gap-closer commit. Note the
  injecting tests (15 sites in `test_act_wiz_command_parity.py`) must be rewritten to populate
  `character_registry` — expect test churn, do it per-family, keep ROM behavior (not the
  injected-fake behavior) as the oracle.
- INV-045's documented residual (message-order-only forward walks) needs no action unless a
  diff-harness scenario observes it.

## Next Steps

1. **Start closing INV-046** — first family: replace
   `mud/commands/imm_commands.py:get_char_world/get_char_room` with delegation to
   `mud.world.char_find` (HANDLER-006-correct), update `imm_punish.py` / `imm_load.py` /
   `remaining_rom.py` imports, rewrite the injecting tests. Then the `imm_server.py` /
   `imm_search.py` / `imm_emote.py` / `player_config.py` `players`-map readers
   (likely `descriptor_list` / `character_registry` walks in ROM). Finish with the Layer-A
   grep-guard so the pattern cannot return.
2. **Fresh probe candidates** after INV-046: mob memory (`src/fight.c` ATTACK_BACK / hunt),
   `update_handler` pulse cadence vs Python tick scheduler, `weather_update` message fan-out
   order.
