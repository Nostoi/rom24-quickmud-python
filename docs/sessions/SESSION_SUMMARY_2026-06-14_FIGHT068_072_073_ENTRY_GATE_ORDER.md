# Session Summary — 2026-06-14 — do_bash / do_dirt entry-gate ordering + `$E` render (FIGHT-068 / FIGHT-072 / FIGHT-073)

## Scope

Continued the `fight.c` offensive-skill **entry-gate** sweep, picking up from
FIGHT-070 (the do_bash is_safe message-surfacing fix). The three remaining MINOR
rows in `docs/parity/FIGHT_C_AUDIT.md` were all entry-gate **early-return order**
or **act()-render** divergences left as follow-ups from the FIGHT-067/069/071
closures — narrow self-target / already-affected edge cases, but real message
divergences from ROM. Closed all three, one gap = one test = one commit.

## Outcomes

### `FIGHT-068` — ✅ FIXED (2.14.105)

- **Python**: `mud/commands/combat.py:do_bash` (~combat.py:443)
- **ROM C**: `src/fight.c:2392-2403`
- **Gap**: Python checked `victim is char` ("You try to bash your brains out, but
  fail.") **before** the `position < POS_FIGHTING` gate; ROM checks position
  **first** (`:2392` before `:2399`). Observable when bashing *yourself* while
  sitting/sleeping: Python emitted the brains-out line where ROM emits the
  position line.
- **Fix**: swapped the two early-return blocks so the position check precedes the
  self-target check.
- **Tests**: 1 — `tests/integration/test_fight068_bash_position_before_self.py`.
  Verified red before, green after.

### `FIGHT-072` — ✅ FIXED (2.14.106)

- **Python**: `mud/commands/combat.py:do_dirt` (~combat.py:1115)
- **ROM C**: `src/fight.c:2522-2532`
- **Gap**: Python checked `victim is char` ("Very funny.") **before** the
  `AFF_BLIND` gate; ROM checks `IS_AFFECTED(victim, AFF_BLIND)` **first** (`:2522`
  before `:2528`). Observable when dirt-kicking *yourself* while already blind:
  Python emitted "Very funny." where ROM emits the blind line. Sibling of
  FIGHT-068.
- **Fix**: swapped the two early-return blocks so the BLIND check precedes the
  self-target check.
- **Tests**: 1 — `tests/integration/test_fight072_dirt_blind_before_self.py`.
  Verified red before, green after.

### `FIGHT-073` — ✅ FIXED (2.14.107)

- **Python**: `mud/commands/combat.py:do_dirt` (~combat.py:1119)
- **ROM C**: `src/fight.c:2524`
- **Gap**: the already-blind message was the literal `"They're already
  blinded."`; ROM emits `act("$E's already been blinded.", ch, NULL, victim,
  TO_CHAR)` — `$E` = victim subjective pronoun, first letter capitalized → "He's
  already been blinded." for a male victim. Wrong pronoun-render AND wrong wording
  ("They're" vs "$E's", "blinded" vs "been blinded").
- **Fix**: `act_format("$E's already been blinded.", recipient=char, actor=char,
  arg2=victim)` (act_format caps the first visible letter via INV-029). Same
  act()-render class as TRIP-001/FIGHT-064.
- **Tests**: 1 — `tests/integration/test_fight073_dirt_blind_pronoun_message.py`
  (blind male victim → "He's already been blinded."). Verified red before, green
  after.

## Out-of-scope bug filed (durable)

- **`FIGHT-075`** — `do_bash`'s position-gate message is the literal "You'll have
  to let **them** get back up first.", where ROM renders `act("...$M...")` (victim
  objective pronoun, `src/fight.c:2394`). Surfaced while closing FIGHT-068 (the
  order swap fixed *which* gate fires; the message text is a separate act()-render
  divergence, sibling of FIGHT-073). Filed 🔄 OPEN in `docs/parity/FIGHT_C_AUDIT.md`.

## Files Modified

- `mud/commands/combat.py` — `do_bash` (position/self-target order swap),
  `do_dirt` (BLIND/self-target order swap + `$E`-rendered blind message).
- `tests/integration/test_fight068_bash_position_before_self.py` — new (1 test).
- `tests/integration/test_fight072_dirt_blind_before_self.py` — new (1 test).
- `tests/integration/test_fight073_dirt_blind_pronoun_message.py` — new (1 test).
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-068/072/073 → ✅ FIXED; added
  FIGHT-075 (🔄 OPEN, the do_bash position-message `$M` render).
- `CHANGELOG.md` — added 2.14.105 / 2.14.106 / 2.14.107 sections.
- `pyproject.toml` — 2.14.104 → 2.14.107.

## Test Status

- `pytest -n0 tests/integration/test_fight068_…` / `…fight072_…` / `…fight073_…`
  — 3/3 (each verified red before its fix).
- `pytest -k bash` — 35 passed; `pytest -k dirt` — 33 passed.
- `pytest tests/integration/ -k "bash or dirt or trip or fight or kill or combat"`
  — 352 passed, 2 skipped.
- `ruff check .` — clean. Pre-commit hooks (ruff, ruff-format, equipment-key,
  char.inventory) all passed.
- GitNexus `impact` on `do_bash` / `do_dirt` — LOW risk, 0 affected processes
  (only caller is `_mob_offensive_skill`). Index reindexed after each commit.

## Next Steps

The fight.c offensive-skill entry-gate **ordering/message** follow-ups are now
exhausted (FIGHT-067/069/070/071/074 + this session's 068/072/073). Open rows:

- **`FIGHT-075`** — do_bash position-message `$M` render (act()-render class, this
  session's spin-off; a 1-line `act_format` fix + test).
- **`INV-050`** — the bigger lever: converge the remaining ~8 silent-bool
  `mud/combat/safety.py:is_safe` callers onto the faithful message-mirror
  `_kill_safety_message` (or retire the bool). do_bash is converged (FIGHT-070);
  spec_funs, assist, apply_damage re-check (FIGHT-002 — *intentionally* silent,
  confirm against `src/fight.c:725-733` before converting), consider,
  thief_skills, do_cast remain. Tracked ⚠️ PARTIAL in
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
- Beyond fight.c, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield
  open lever remains the **Hypothesis state-machine → diff_harness widening**
  (Class 11 / Phase C), enumeration-independent (guardrail 3).
