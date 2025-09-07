## Port Instructions (ROM 2.4 → Python) — Living Rules

<!-- RULES-START -->
- RULE: All combat randomness must use the ROM Mitchell–Moore `number_mm` family (`seed_mm`, `number_range`, `number_percent`, `dice`, `number_bits`); forbid `random.*` in combat paths.
  RATIONALE: Preserves ROM hit/damage distributions and exact RNG sequence.
  EXAMPLE: rng_mm.seed_mm(1234); rng_mm.number_percent()

- RULE: Use C-semantics helpers `c_div` and `c_mod` in all combat math; forbid `//` and `%` in ported code.
  RATIONALE: C truncates toward zero; Python floors; negatives diverge.
  EXAMPLE: c_div(-3, 2) == -1  # matches C

- RULE: Armor Class is better when more negative; map damage type → AC index exactly as in ROM.
  RATIONALE: Prevents inverted hit curves and weapon-type bias.
  EXAMPLE: dam_type "slash" → AC_SLASH; unarmed → AC_BASH

- RULE: Preserve defense check order exactly (hit roll → shield block → parry → dodge), each early-outs on success.
  RATIONALE: Reordering changes effective probabilities.
  EXAMPLE: assert call_order == ["hit", "shield", "parry", "dodge"]

- RULE: Dice are inclusive (1..size); apply modifiers after base dice, then apply RIV (IMMUNE=0, RESIST=½, VULN=×2 unless fork differs) before side-effects.
  RATIONALE: Off-by-one and wrong ordering skew damage and status logic.
  EXAMPLE: dmg = dice(n,s) + str_mod + damroll; dmg = apply_riv(dmg, dam_type)

- RULE: Match tick cadence and WAIT/DAZE consumption to ROM’s `PULSE_VIOLENCE`; do not change update ordering.
  RATIONALE: Attack frequency and regen timing must align to parity.
  EXAMPLE: scheduler.every(PULSE_VIOLENCE)(violence_update)

- RULE: File formats (areas/help/player saves) must parse/serialize byte-for-byte compatible fields and ordering.
  RATIONALE: Tiny text/layout changes break content and saves.
  EXAMPLE: save_player() writes fields in ROM order; golden read/write round-trip test passes
- RULE: Wiznet channels must mirror ROM wiznet flag bits and levels; track immortal subscriptions.
  RATIONALE: Ensures admin communications match ROM visibility.
  EXAMPLE: wiznet("Imm info", WIZ_ON, ch)
- RULE: Track affects and saving throws with bitmask flags; avoid Python booleans.
  RATIONALE: ROM uses fixed-width bit flags; parity requires bitwise operations.
  EXAMPLE: ch.affected_by |= AFF_BLIND
- RULE: Define affect flags via `IntFlag` with explicit bit values; forbid magic numbers.
  RATIONALE: Ensures flag widths match ROM and improves readability.
  EXAMPLE: class AffectFlag(IntFlag): BLIND = 0x00000001
- RULE: Manipulate character affects via `add_affect`/`remove_affect`; forbid direct bit twiddling in game logic.
  RATIONALE: Central helpers preserve future side effects and keep flag math consistent.
  EXAMPLE: ch.add_affect(AffectFlag.BLIND)
- RULE: Dispatch social commands via registry loaded from ROM `social.are`; forbid hard-coded emote strings.
  RATIONALE: Maintains ROM social messaging and target handling.
  EXAMPLE: social = social_registry["smile"]; social.execute(ch, victim)
- RULE: Expand social messages with ROM placeholders (`$n`, `$N`, `$mself`) before dispatch.
  RATIONALE: Ensures actor and target names/pronouns match ROM outputs.
  EXAMPLE: expand_social("$n smiles at you.", ch, vict)
- RULE: Lowercase social command names on registration to ensure case-insensitive lookup.
  RATIONALE: ROM treats social commands without regard to case.
  EXAMPLE: social_registry[social.name.lower()] = social
- RULE: Convert `social.are` to JSON preserving field widths; verify with golden file tests.
  RATIONALE: ROM social lines are fixed-width; reformatting alters parsing.
  EXAMPLE: convert_social_are("data/social.are")
- RULE: Format social messages via `expand_placeholders`; forbid f-strings or `.format` for names.
  RATIONALE: Preserves ROM placeholder semantics and pronoun expansion.
  EXAMPLE: expand_placeholders("$n nods at $N.", ch, vict)
- RULE: Advance world time using ROM `time_info`; emit sunrise/sunset messages on `PULSE_TICK`.
  RATIONALE: Day/night transitions affect light levels and time-based effects.
  EXAMPLE: time_info.update(); broadcast("The sun rises in the east.")
- RULE: Block movement when `carry_weight` or `carry_number` exceed strength limits; update on inventory changes.
  RATIONALE: ROM prevents over-encumbered characters from moving.
  EXAMPLE: if ch.carry_weight > can_carry_w(ch): return "You are too heavy to move."
- RULE: Serve help topics via registry loaded from ROM help JSON; dispatch `help` command through keyword lookup.
  RATIONALE: Preserves ROM help text layout and keyword search behavior.
  EXAMPLE: text = help_registry["murder"].text
- RULE: Invoke NPC special functions via registry each tick; avoid hard-coded checks.
  RATIONALE: ROM uses spec_fun pointers for mob AI; registry preserves behaviors.
  EXAMPLE: spec_fun = spec_fun_registry.get(ch.spec_fun); spec_fun(ch)
- RULE: Log admin commands to `log/admin.log` and rotate daily.
  RATIONALE: Ensures immortal actions are auditable like ROM's wiznet logs.
  EXAMPLE: ban bob  # appends line to log/admin.log
- RULE: Register `wiznet` command in dispatcher; restrict usage to immortals and toggle flag bits via helper.
  RATIONALE: Keeps admin communications controlled and consistent with ROM wiznet flags.
  EXAMPLE: command_registry["wiznet"] = wiznet_cmd; wiznet_cmd(ch, "show")
- RULE: Define wiznet flags via IntFlag with explicit bit values; forbid magic numbers.
  RATIONALE: Ensures wiznet subscriptions use consistent bitmask widths.
  EXAMPLE: class WiznetFlag(IntFlag): WIZ_ON = 0x00000001
- RULE: Resolve saving throws with `rng_mm.number_percent` and `c_div`; forbid Python `%` or boolean short-circuit.
  RATIONALE: Preserves ROM probability and C arithmetic for saves.
  EXAMPLE: save = rng_mm.number_percent() < c_div(level * 3, 2)
- RULE: Index `area_registry` by area vnum; forbid filename keys.
  RATIONALE: ROM looks up areas by vnum; string keys break reset lookup.
  EXAMPLE: area_registry[area.min_vnum] = area
- RULE: Reject duplicate area vnum ranges when loading; raise `ValueError` on conflict.
  RATIONALE: Overlapping vnum ranges corrupt world lookups.
  EXAMPLE: load_area_file("mid.are"); load_area_file("mid.are")  # ValueError
- RULE: Require `$` sentinel at end of `area.lst`; raise `ValueError` if missing.
  RATIONALE: ROM uses `$` to terminate area lists; missing sentinel risks partial loads.
  EXAMPLE: load_all_areas("bad.lst")  # ValueError
<!-- RULES-END -->

## Ops Playbook (human tips the bot won’t manage)
- Use `rg` for code searches; never run `grep -R`.
- Quote paths with spaces (e.g., `src/'QuickMUD Fixes'`).
- Update `doc/c_module_inventory.md` whenever C modules are added or removed.
- Always run `pytest` before committing.
- Maintain `doc/python_module_inventory.md` when Python modules change; keep C feature mapping current.
- Keep `doc/c_python_cross_reference.md` updated when subsystems move from C to Python.
- Maintain JSON schemas under `schemas/`; revise them whenever data formats change.
- Keep `schemas/character.schema.json` aligned with `char_data`; include new stats or flags immediately.
- Keep `schemas/object.schema.json` aligned with `OBJ_DATA`; update wear flags and value slots when they change.
- Keep `schemas/area.schema.json` aligned with `AREA_DATA`; capture vnum ranges and builder lists precisely.
- Validate every JSON schema with `jsonschema` tests; update tests when schemas change.
- Always convert `.are` files using `mud/scripts/convert_are_to_json.py`; never handcraft JSON.
- Clear registries before conversions to avoid leaking data between areas.
- Store converted area JSON under `data/areas/`; name files after the source `.are`.
- Verify converted area JSON preserves room, mob, and object counts; tests must compare against source `.are` files.
- Mirror each JSON schema with a `*_json.py` dataclass; update `mud/models/__init__.py` and `mud/models/README.md`.
- Enumerate C subsystems in `PYTHON_PORT_PLAN.md`; never begin porting a module without a corresponding plan entry.
- Run mypy with `--follow-imports=skip` on targeted modules to avoid unrelated type errors.
- Ensure schema defaults mirror dataclass defaults; test instantiation to catch mismatches.
- Convert `#SHOPS` sections with `convert_shops_to_json.py`; map item type numbers to `ItemType` names and skip zeros.
- Cross-check converted table counts with source files; fail tests on mismatches.
- Make every schema dataclass subclass `JsonDataclass`; never hand-roll JSON serialization.
- Stop cloning `merc.h` structs; favor schema dataclasses like `ResetJson`.
- Create runtime dataclasses mirroring each schema; never operate on JSON dataclasses inside the engine.
- Reset ticks must clear mobs and objects before reapplying area resets.
- Test reset scheduler with ticks to ensure repop occurs when areas empty.
- Drive command dispatch through a Command dataclass; match unique prefixes and block admin-only commands in dispatcher.
- Use `shlex.split` for argument parsing; reject ambiguous abbreviations as unknown commands.
- Force hits or misses by cranking hitroll; don’t seed global RNG in tests.
- Flip positions correctly on swing/kill; remove corpses and grant XP in ROM order.
- Drive all skill usage through `skill_registry`; never hard-code spell lists.
- Inject RNG into `SkillRegistry` for deterministic failure tests.
- Level-ups must call `advance_level`; never set `level` directly.
- Practice/train must consume sessions and validate targets.
- Shop prices must use `shop.profit_buy/profit_sell`; never charge raw object cost.
- Write player saves atomically (temp file + `os.replace`).
- Strip `comm.c`, `nanny.c`, and `telnet.h` once networking is Python-only; update docs immediately.
- Translate ROM color tokens with `translate_ansi` before sending to clients.
- In telnet tests with multiple clients, wait for prompts to flush broadcasts.
- Route global channels through `broadcast_global`; respect mutes/bans.
- Clear `character_registry` in channel tests to avoid cross-test contamination.
- Persist boards under `data/boards` with atomic writes; override paths in tests.
- Register `note`/`board` commands in the dispatcher; keep the command table authoritative.
- Represent mobprog triggers with `IntFlag`; match trigger bits precisely.
- `run_prog` should return executed actions for tests; ignore unsupported commands.
- Put OLC commands in `commands/build.py`; guard them as admin-only; return usage on bad args.
- Verify `@redit` updates `Room` fields in-place via dispatcher tests.
- Tick order: regen → weather → timers → resets (match ROM cadence).
- Filter character loads by account username; never allow cross-account access.
- Prompt account then password; auto-create missing accounts in tests only.
- Reset DB tables before telnet login tests.
- Hash passwords via `hash_password` (salted); never use `hashlib` directly.
- Ensure password tokens are `salt:hash`; tests must verify uniqueness & reject malformed tokens.
- Exercise the full command loop with `run_test_session`; remove placeholder tests.
- Keep CI (ruff/mypy/pytest/coverage) current with new modules.
- Enforce `--cov-fail-under=80` in CI.
- Delete obsolete C modules and docs once replaced.
- Docker must launch `mud runserver`; never reference the old C binary.
- Remove the entire `src/` tree; do not commit C code again.
