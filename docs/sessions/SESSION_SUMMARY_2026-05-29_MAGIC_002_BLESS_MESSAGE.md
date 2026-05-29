# Session Summary — 2026-05-29 — MAGIC-002 bless message + MAGIC-003 / CAST-002 filed

## Scope

Continued from the `affect_armor` handoff. That session fixed the `armor`
instance of MAGIC-002 (affect spells silent on success through `do_cast`) and
left a note that `bless`/`shield` were "likewise silent" — a documented "sweep"
to port the remaining ROM success messages. This session picked up that sweep:
the recommended next move per `SESSION_STATUS.md`.

The investigation found the audit doc's premise was **partly wrong**. Most
affect-buff handlers (`armor`, all `detect_*`, `fly`, `frenzy`, `giant_strength`,
`haste`, `calm`, `pass_door`, …) already deliver via the canonical
`_send_to_char`/`broadcast_room`. Only **`bless`** is *genuinely silent* on
success. `shield`/`sanctuary`/`weaken`/`blindness` are **not** silent — they
deliver via the divergent `char.messages.append` mailbox channel, a different
bug. So the session closed the one true silent instance (`bless`) cleanly and
filed the rest as correctly-scoped siblings (MAGIC-003, CAST-002).

## Outcomes

### `MAGIC-002` (bless instance) — ✅ FIXED (2.11.21)

- **Python**: `mud/skills/handlers.py:bless`
- **ROM C**: `src/magic.c:836-865` (`spell_bless`, character branch)
- **Gap**: `bless` applied the +hitroll / −saving-throw affect but was **silent**
  on success, and the already-affected branch returned `False` with no message at
  all. Since `do_cast` is silent on a successful cast (FINDING-013), the line was
  dropped entirely.
- **Fix**: `bless` now mirrors ROM `spell_bless` character-target messaging:
  - success: `"You feel righteous."` (TO_VICT) + `act("You grant $N the favor of
    your god.")` (TO_CHAR, cross-target only);
  - already-affected branch — which ROM also takes when `victim->position ==
    POS_FIGHTING` (`src/magic.c:840`, a deliberate quirk: a fighting target reads
    as already-blessed even with no bless affect) — sends `"You are already
    blessed."` (self) / `act("$N already has divine favor.")` (cross-target).
  - The `spell_bless` **object-target** branch (`TAR_OBJ_CHAR_DEF` obj case,
    `src/magic.c:788-834`) is **deferred** — unreachable until `do_cast` routes
    object targets (MAGIC_C_AUDIT.md Scope Notes); no dead code added.
  - Side benefit: `holy_word`'s `bless` sub-cast (`src/magic.c:3304`) now
    faithfully emits the bless line to affected targets.
- **Tests**: `tests/integration/test_magic_002_bless_message.py` — 5 tests, all
  green (self-cast success, cross-target both-sides, already-affected self,
  already-affected cross-target, POS_FIGHTING quirk). Failing-first verified. The
  two no-arg self-cast tests exercise the handler directly because `do_cast`'s
  self-default is itself broken for this target type — see CAST-002.

### `MAGIC-003` — filed (🔄 OPEN) — wrong-channel affect-message delivery

- **Python**: `mud/skills/handlers.py` — `shield` (7113), `sanctuary` (7071),
  `weaken` (7907, room leg only), `blindness` (1505).
- **ROM C**: `src/magic.c:4296-4297` (sanctuary), `:4326-4327` (shield),
  `:888-889` (blindness), `:4580-4581` (weaken).
- **Gap**: these handlers deliver success / room-broadcast messages via the
  divergent `char.messages.append` mailbox channel instead of canonical
  `push_message` (`_send_to_char`) / `broadcast_room`. Not silent (a connected PC
  still gets it via the connection drain) and not double-delivery (INV-001) — but
  a TO_ROOM broadcast to a connected *bystander* arrives on that bystander's next
  prompt instead of immediately, and the differential harness (reading the
  descriptor) sees nothing. **Needs a connected-PC test** — mailbox-only tests
  pass before any fix (`push_message` and raw `.append` both land in `.messages`
  for a test char). Template: `tests/integration/test_broadcast_room_single_delivery.py`.
- INV-001 SINGLE-DELIVERY family. Filed in `docs/parity/MAGIC_C_AUDIT.md`.

### `CAST-002` — filed (🔄 OPEN) — do_cast TAR_OBJ_CHAR_DEF self-default

- **Python**: `mud/commands/combat.py` (`do_cast` target dispatch).
- **ROM C**: `src/magic.c:514-535` (`TAR_OBJ_CHAR_DEF`) vs `:466-512`
  (`TAR_OBJ_CHAR_OFF`); `src/const.c` per-spell `TAR_*`.
- **Gap**: `do_cast` maps the `"character_or_object"` skill-target string to the
  *offensive* default (fighting victim; `"Cast the spell on whom?"` when not
  fighting), conflating two ROM target types. The 5 spells tagged
  `character_or_object` split: **defensive** `TAR_OBJ_CHAR_DEF` (no-arg → self) =
  `bless`, `invisibility`, `remove curse`; **offensive** `TAR_OBJ_CHAR_OFF`
  (no-arg → fighting victim) = `curse`, `poison`. The 3 defensive ones wrongly
  error `"Cast the spell on whom?"` on a no-arg self-cast instead of defaulting to
  self. Surfaced while writing the bless self-cast tests. CAST-001 sibling. Filed
  in `docs/parity/MAGIC_C_AUDIT.md`.

## Files Modified

- `mud/skills/handlers.py` — `bless` delivers ROM `spell_bless` character-target messaging
- `tests/integration/test_magic_002_bless_message.py` — 5 regression tests (new)
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-002 row → ✅ FIXED (armor + bless), "shield is silent" claim corrected; MAGIC-003 + CAST-002 rows added
- `CHANGELOG.md` — `## [2.11.21]` Fixed entry
- `pyproject.toml` — 2.11.20 → 2.11.21

Commit: `47d6ce53` (single `fix(parity)` commit).

## Test Status

- `pytest tests/integration/test_magic_002_bless_message.py` — 5/5 passing.
- Wider net `pytest -k "bless or holy_word or cast or spell"` — 695 passed.
- Full suite (master `47d6ce53`): **4963 passed, 4 skipped** (~147s; +5 vs the
  prior 4958 from `test_magic_002_bless_message.py`).
- `ruff check` clean on the bless edit region (pre-existing F841 debt at
  handlers.py 672/1782/3517/3664/6297 left untouched — not introduced this session).
- `gitnexus_detect_changes`: LOW risk, scope = `bless` + audit-doc sections
  (`blindness` flagged as "touched" is a line-shift artifact — the diff is bless-only).

## Outstanding

- **`CAST-002` (OPEN)** — highest-value next move: a player-facing bug (no-arg
  `cast bless` / `cast invis` / `cast 'remove curse'` errors instead of
  self-casting). Touches `do_cast` target dispatch (blast radius = every spell),
  so do impact analysis first. Likely needs the skills.json target vocabulary to
  distinguish defensive vs offensive `character_or_object`.
- **`MAGIC-003` (OPEN)** — channel-migration sweep (shield/sanctuary/weaken/
  blindness → canonical delivery). Lower value (functionally delivers today); the
  real symptom is late bystander broadcasts. Needs a connected-PC test.
- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template. RNG-stream
  scope; breaks existing pet-shop gold assertions.
- **`affect_flags` case-normalization** (diff-harness, deferred) — fix when adding
  the first flag-setting affect scenario (sanctuary/haste).
- **`test_combat_death.py` xdist flake** (carried) — seed RNG in the unit death tests.
- Stray uncommitted 1-line doc tweak to `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`
  (present in both worktrees; unrelated to parity — left uncommitted).

## Next Steps

Close **`CAST-002`** next — it is the only player-facing bug in the residual set
(three common defensive spells can't be self-cast with no target). It is
well-scoped (defensive `TAR_OBJ_CHAR_DEF` should default to self, `src/magic.c:514-519`),
but touches `do_cast` so run `gitnexus_impact` first and lean on the existing
CAST-001 tests. Then `MAGIC-003` (needs a connected-PC delivery test). Both close
out the MAGIC-002 affect-message family.
