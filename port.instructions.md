## Port Instructions (ROM 2.4 -> Python) — Living Rules

<!-- RULES-START -->

- RULE: All combat randomness must use the ROM Mitchell–Moore `number_mm` family (`seed_mm`, `number_range`, `number_percent`, `dice`, `number_bits`); forbid `random.*` in combat paths.
  RATIONALE: Preserves ROM hit/damage distributions and exact RNG sequence.
  EXAMPLE: rng_mm.seed_mm(1234); rng_mm.number_percent()

- RULE: Use C-semantics helpers `c_div` and `c_mod` in all combat math; forbid `//` and `%` in ported code.
  RATIONALE: C truncates toward zero; Python floors; negatives diverge.
  EXAMPLE: c_div(-3, 2) == -1 # matches C

- RULE: Armor Class is better when more negative; map damage type -> AC index exactly as in ROM.
  RATIONALE: Prevents inverted hit curves and weapon-type bias.
  EXAMPLE: dam_type "slash" -> AC_SLASH; unarmed -> AC_BASH

- RULE: Preserve defense check order exactly (hit roll -> shield block -> parry -> dodge), each early-outs on success.
  RATIONALE: Reordering changes effective probabilities.
  EXAMPLE: assert call_order == ["hit", "shield", "parry", "dodge"]

- RULE: Dice are inclusive (1..size); apply modifiers after base dice, then apply RIV (IMMUNE=0, RESIST=½, VULN=×2 unless fork differs) before side-effects.
  RATIONALE: Off-by-one and wrong ordering skew damage and status logic.
  EXAMPLE: dmg = dice(n,s) + str_mod + damroll; dmg = apply_riv(dmg, dam_type)

- RULE: Match tick cadence and WAIT/DAZE consumption to ROM’s `PULSE_VIOLENCE`; do not change update ordering.
  RATIONALE: Attack frequency and regen timing must align to parity.
  EXAMPLE: scheduler.every(PULSE_VIOLENCE)(violence_update)

- RULE: Skills and spells must honor ROM WAIT_STATE pulses: set `Character.wait = max(wait, skill.lag)` using skill beats, halve lag when AFF_HASTE is set, double lag when AFF_SLOW is set, and reject attempts while wait > 0 with the recovery message.
  RATIONALE: ROM `WAIT_STATE` enforces recovery windows and affect-driven tempo; skipping it allows spammable abilities.
  EXAMPLE: SkillRegistry.use applies `_compute_skill_lag` and `_apply_wait_state`; tests/test_skills.py::test_skill_use_sets_wait_state_and_blocks_until_ready

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
- RULE: Check character affects with `has_affect`; forbid inline bitmask tests.
  RATIONALE: Central helper mirrors ROM macros and avoids scattered bit logic.
  EXAMPLE: if ch.has_affect(AffectFlag.BLIND): ...
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

- RULE: Over-encumbrance imposes a wait-state; overweight move attempts should increase `ch.wait` using ROM `WAIT_STATE` semantics.
  RATIONALE: Movement penalties from weight are enforced via lag/wait in ROM.
  EXAMPLE: if ch.carry_weight > can_carry_w(ch): WAIT_STATE(ch, PULSE_VIOLENCE/2)

- RULE: Hour advances on ROM `PULSE_TICK` (60 × `PULSE_PER_SECOND`), not every 4 pulses; tests may scale ticks but engine cadence must match ROM.
  RATIONALE: `update_handler` increments time on `pulse_point == 0` (i.e., `PULSE_TICK`), which triggers `weather_update` and sunrise/sunset.
  EXAMPLE: if pulses_since_tick >= PULSE_TICK: advance_hour(); pulses_since_tick = 0

- RULE: Skill/spell success and failure must roll with `rng_mm.number_percent()` (1..100); forbid `Random.random()` in skills.
  RATIONALE: ROM evaluates against a percent roll; using floats changes distribution and parity.
  EXAMPLE: if rng_mm.number_percent() <= learned: succeed()

- RULE: Skill metadata JSON must retain ROM `skill_table` fields (per-class levels, rating costs, slot numbers, min_mana, beats) and expose them to practice/train flows.
  RATIONALE: Trainers gate access and advancement on these fields; mana drain and casting lag derive from `skill_table` metadata.
  EXAMPLE: data/skills.json["acid blast"] includes level/rating arrays, slot 70, min_mana 20, beats 12 consumed by `do_practice` tests.

- RULE: THAC0-based hit resolution uses `number_bits(5)` diceroll and `compute_thac0` (class-based) when `COMBAT_USE_THAC0` is enabled; tests must patch the engine module flag.
  RATIONALE: Mirrors ROM hit calculation while keeping default behavior stable.
  EXAMPLE: monkeypatch.setattr('mud.combat.engine.COMBAT_USE_THAC0', True)

- RULE: Conversions from `area/*.are` must preserve counts (ROOMS/MOBILES/OBJECTS/RESETS/SHOPS/SPECIALS), exit flags/doors/keys, extra descriptions, and `$` sentinels.
  RATIONALE: Prevent silent data loss.
  EXAMPLE: `pytest -q tests/test_area_counts.py::test_midgaard_counts`

- RULE: Player save JSON must preserve ROM bit widths and field order; never reorder keys that map to packed flags.
  RATIONALE: Save/load parity.
  EXAMPLE: `save_load_roundtrip("Shemp")`
- RULE: Persist ROM condition slots (`Cnd` drunk/full/hunger/thirst) when converting and saving players.
  RATIONALE: Survival timers and thirst/hunger effects rely on these counters; dropping them on save/reset deviates from ROM behavior.
  EXAMPLE: `tests/test_player_save_format.py::test_condition_roundtrip`
- RULE: Player saves must retain ROM identity and progression fields (race/class/sex/trust/security, creation points, HMVP perm stats).
  RATIONALE: Reboots that drop these fields reset classes, stats, and hit/mana pools, breaking parity with ROM `fwrite_char` records.
  EXAMPLE: `tests/test_player_save_format.py::test_identity_fields_roundtrip`
- RULE: Player converters must accept ROM `print_flags` zero sentinels (`'0'`) for flag fields.
  RATIONALE: ROM writes `Comm`/`Wizn` lines with `'0'` when no bits are set; rejecting them prevents clean loads.
  EXAMPLE: `convert_player("player_zero_comm")`
- RULE: Player converters must decode ROM lowercase `print_flags` letters (bits 26–31) into the correct mask positions.
  RATIONALE: ROM emits lowercase `a`..`f` for high bits; treating them as invalid drops wiznet/act flags during conversion.
  EXAMPLE: `convert_player("player_wiznet_ticks")`

- RULE: IMC parsing behind feature flag; parsers validated with sample frames; no sockets when disabled.
  RATIONALE: Wire compatibility without runtime coupling.
  EXAMPLE: `IMC_ENABLED=False`

- RULE: Implement ROM gating loops for RNG: `number_percent`, `number_range`, and `number_bits` must derive from `number_mm` with bitmask + `while` gating exactly as in `src/db.c`; `dice(n,size)` sums `number_range(1,size)` n times.
  RATIONALE: Bitmask gating avoids out‑of‑range values and matches ROM sequences; direct `getrandbits` or `randint` changes parity.
  EXAMPLE: while ( (percent = number_mm() & 127) > 99 ) ; return 1 + percent

- RULE: Apply ROM reset semantics for 'P' nesting and limits; track `LastObj`/`LastMob` during area resets and respect `arg2` limits and lock-state fix-ups.
  RATIONALE: Vnum-keyed placement loses instance order and breaks container contents; limit/lock semantics matter for canonical areas.
  EXAMPLE: after 'O' creates container C (LastObj=C), 'P' places items into C until `count_obj_list` reaches arg4; then `C->value[1] = C->pIndexData->value[1]`.
- RULE: Area resets must skip 'O'/'P'/'G'/'E' placements while `area.nplayer > 0`, reuse `LastObj`/`LastMob`, honour `OBJ_INDEX_DATA->count` limits with the 1-in-5 reroll, and bump prototype counts on spawn.
  RATIONALE: Donation pits, desks, and shopkeeper inventories rely on ROM gating; ignoring it floods rooms with duplicates and disables world caps.
  EXAMPLE: pytest -q tests/test_spawning.py::test_resets_room_duplication_and_player_presence
- RULE: Reset loaders must mirror ROM `load_resets` parsing: ignore `if_flag`, set `arg1..arg4` like C, and keep mob/object limits for 'M'/'P'.
  RATIONALE: Dropping reset arguments erases ROM spawn caps and duplicates mobs/objects.
  EXAMPLE: convert_area('midgaard.are') → ResetJson(command='M', arg1=3000, arg2=1, arg3=3033, arg4=1)
- RULE: Reset handlers must honor 'D' commands by restoring exit `rs_flags`/`exit_info` on every reset.
  RATIONALE: Door states must re-close and relock after resets to match ROM gating.
  EXAMPLE: pytest -q tests/test_spawning.py::test_door_reset_applies_closed_and_locked_state
- RULE: Reset cycles must refresh each exit's `exit_info` from `rs_flags` (and mirror reverse exits) before processing commands.
  RATIONALE: ROM `reset_room` copies baseline door flags every tick so unlabeled doors return to their default state even without an explicit 'D'.
  EXAMPLE: pytest -q tests/test_spawning.py::test_reset_restores_base_exit_state
- RULE: Reset scheduling must mirror ROM `area_update`: age every area, reset after three empty area-minutes, and force a reset once age ≥15 with players or ≥31 regardless of population.
  RATIONALE: Populated areas still repopulate in ROM; skipping the 15/31-minute gates leaves cities permanently looted.
  EXAMPLE: pytest -q tests/test_spawning.py::test_area_reset_schedule_matches_rom
- RULE: Reset passes must not clear rooms before running commands; reuse LastMob/LastObj counters so player-dropped items persist unless a reset removes them.
  RATIONALE: Clearing contents deletes loot and bypasses ROM spawn limits enforced by `count_obj_list`/`pObjIndex->count`.
  EXAMPLE: pytest -q tests/test_spawning.py::test_reset_does_not_wipe_room_contents
- RULE: Mob programs must expose ROM trigger APIs (mp_percent/mp_exit/mp_greet) and execute scripts via `program_flow` calling the command interpreter; forbid stub executors that only echo strings.
  RATIONALE: Trigger gating and command dispatch keep NPC scripts in sync with ROM behaviors and side effects.
  EXAMPLE: pytest -q tests/test_mobprog_triggers.py::test_program_flow_runs_commands_via_dispatcher

- RULE: Mob command interpreter must register the full ROM `mob` verb table (asound/zecho/mload/oload/transfer/force/kill/etc.) and implement their side effects.
  RATIONALE: Area scripts depend on these verbs to spawn actors, broadcast alarms, force actions, and manage combat; missing handlers silently break quests.
  EXAMPLE: pytest -q tests/test_mobprog_commands.py::test_spawn_and_transfer_commands

- RULE: Enforce command required positions before dispatch; mirror ROM denial messages for position < required.
  RATIONALE: Prevents actions while sleeping/fighting/etc. and matches gameplay semantics.
  EXAMPLE: if ch.position < POS_RESTING: "Nah... You feel too relaxed..."

- RULE: Charge movement points by sector and apply short wait on moves; require boat for noswim and fly for air.

<!-- ENHANCED-EVIDENCE-RULES-START -->

# Enhanced Evidence Framework for Final Completion Phase

- RULE: INTEGRATION evidence must demonstrate cross-subsystem interaction with concrete test cases.
  RATIONALE: Individual task completion doesn't guarantee architectural coherence; integration failures cause task-completion disconnect.
  EXAMPLE: INTEGRATION: tests/integration/test_reset_movement.py demonstrates reset state consistency during player movement

- RULE: PERFORMANCE evidence must include ROM baseline comparisons with specific timing measurements.
  RATIONALE: Python implementation must maintain ROM gameplay timing for authentic experience.
  EXAMPLE: PERFORMANCE: Reset cycle completes within 500ms (ROM baseline: 450ms ±10%)

- RULE: ARCHITECTURAL evidence must trace critical state variables across subsystem boundaries.
  RATIONALE: Complex systems like resets/movement require state tracking beyond individual functions.
  EXAMPLE: ARCHITECTURAL: LastObj/LastMob state maintained consistently across reset_room, char_to_room, and save/load cycles

- RULE: COMPLETION evidence requires both individual task validation AND integration test success.
  RATIONALE: Completed individual tasks without integration validation creates false completion status.
  EXAMPLE: COMPLETION: All P0 tasks ✅ AND tests/integration/test\_[subsystem]\_integration.py passes

- RULE: CONFIDENCE scoring must weight integration test results more heavily than individual task completion.
  RATIONALE: Integration failures indicate deeper architectural issues that individual task fixes cannot resolve.
  EXAMPLE: CONFIDENCE: max(0.5, task_completion _ 0.3 + integration_success _ 0.7)
  <!-- ENHANCED-EVIDENCE-RULES-END -->
  RATIONALE: Movement economy and gating are core to ROM exploration pacing.
  EXAMPLE: move_cost = (movement_loss[from] + movement_loss[to]) / 2; WAIT_STATE(ch,1)
- RULE: Block movement when `carry_weight` or `carry_number` exceed strength limits; update on inventory changes.
  RATIONALE: ROM prevents over-encumbered characters from moving.
  EXAMPLE: if ch.carry_weight > can_carry_w(ch): return "You are too heavy to move."
- RULE: Charmed followers (AFF_CHARM) must refuse to leave while their master shares the room, returning the ROM loyalty message.
  RATIONALE: `move_char` blocks AFF_CHARM characters from wandering away from their controllers.
  EXAMPLE: pytest -q tests/test_movement_charm.py::test_charmed_character_cannot_leave_master_room
- RULE: Movement must move eligible followers with the leader and fire mobprog exit/greet triggers after relocation.
  RATIONALE: ROM `move_char` recursively moves followers and calls `mp_exit_trigger`/`mp_greet_trigger`, keeping escorts and scripts synchronized.
  EXAMPLE: pytest -q tests/test_movement_followers.py::test_followers_move_and_trigger_mobprogs
- RULE: Serve help topics via registry loaded from ROM help JSON; dispatch `help` command through keyword lookup.
  RATIONALE: Preserves ROM help text layout and keyword search behavior.
  EXAMPLE: text = help_registry["murder"].text
- RULE: Invoke NPC special functions via registry each tick; avoid hard-coded checks.
  RATIONALE: ROM uses spec_fun pointers for mob AI; registry preserves behaviors.
  EXAMPLE: spec_fun = spec_fun_registry.get(ch.spec_fun); spec_fun(ch)
- RULE: Log admin commands to `log/admin.log` and rotate daily.
  RATIONALE: Ensures immortal actions are auditable like ROM's wiznet logs.
  EXAMPLE: ban bob # appends line to log/admin.log
- RULE: Register `wiznet` command in dispatcher; restrict usage to immortals and toggle flag bits via helper.
  RATIONALE: Keeps admin communications controlled and consistent with ROM wiznet flags.
  EXAMPLE: command_registry["wiznet"] = wiznet_cmd; wiznet_cmd(ch, "show")
- RULE: Define wiznet flags via IntFlag with explicit bit values; forbid magic numbers.
  RATIONALE: Ensures wiznet subscriptions use consistent bitmask widths.
  EXAMPLE: class WiznetFlag(IntFlag): WIZ_ON = 0x00000001
- RULE: Resolve saving throws with `rng_mm.number_percent` and `c_div`; forbid Python `%` or boolean short-circuit.
  RATIONALE: Preserves ROM probability and C arithmetic for saves.
  EXAMPLE: save = rng_mm.number_percent() < c_div(level \* 3, 2)
- RULE: Index `area_registry` by area vnum; forbid filename keys.
  RATIONALE: ROM looks up areas by vnum; string keys break reset lookup.
  EXAMPLE: area_registry[area.min_vnum] = area
- RULE: Reject duplicate area vnum ranges when loading; raise `ValueError` on conflict.
  RATIONALE: Overlapping vnum ranges corrupt world lookups.
  EXAMPLE: load_area_file("mid.are"); load_area_file("mid.are") # ValueError
- RULE: Require `$` sentinel at end of `area.lst`; raise `ValueError` if missing.
  RATIONALE: ROM uses `$` to terminate area lists; missing sentinel risks partial loads.
  EXAMPLE: load_all_areas("bad.lst") # ValueError
- RULE: Parse `#AREADATA` builders/security/flags into `Area`; forbid skipping this section.
  RATIONALE: ROM stores builder permissions and security in `#AREADATA`; omitting them loses access control.
  EXAMPLE: area = load_area_file('midgaard.are'); assert area.builders and area.security == 9
- RULE: Map `$mself` pronouns by `Sex` (NONE->"itself", MALE->"himself", FEMALE->"herself", others->"themselves").
  RATIONALE: Reflexive pronouns depend on actor sex to match ROM socials.
  EXAMPLE: expand_placeholders("$n laughs at $mself.", ch)
- RULE: Treat areas/\*.are as canonical; conversions must preserve counts, ids, exits, flags, resets, specials.
  RATIONALE: Prevent silent data loss during ROM->JSON migration.
  EXAMPLE: pytest -q tests/test_area_counts.py::test_midgaard_counts
- RULE: Validate conversion with goldens: for each .are, store a {area}.golden.json and assert stable round-trip.
  RATIONALE: Detect accidental schema drift, field reordering, or flag width changes.
  EXAMPLE: tests/data/midgaard.golden.json vs converter output.
- RULE: Player saves must preserve bit widths and field order from /player/\* semantics; never reorder JSON keys that map to packed flags.
  RATIONALE: Prevent save/load parity bugs.
  EXAMPLE: save_load_roundtrip("arthur"); assert flags == expected
- RULE: Document-driven behavior takes precedence; when code and docs disagree, cite C+DOC evidence and lock tests to ROM semantics.
  RATIONALE: Guard against “clean” Python refactors that drift from ROM.
  EXAMPLE: test_thac0_table_matches_rom()
- RULE: IMC code is feature-flagged; if disabled at runtime, keep loader and protocol parsers in place with no-op dispatch.
  RATIONALE: Preserve wire compatibility without enabling cross-MUD chat.
  EXAMPLE: IMC_ENABLED=False -> sockets never opened; parsers tested.
- RULE: Register `spec_fun` names in lowercase for case-insensitive lookup.
  RATIONALE: ROM's `spec_lookup` compares names without regard to case.
  EXAMPLE: register_spec_fun("Spec_Cast_Adept", func)
- RULE: Enforce site/account bans at login using a ban registry; persist bans in ROM-compatible format and field order.
  RATIONALE: Security parity with ROM (`check_ban`/`do_ban`); prevents banned hosts/accounts from entering.
  EXAMPLE: add_ban(host="bad.example", type="all"); assert login(host) == "BANNED"
- RULE: Shop commands must respect `Shop.open_hour`/`close_hour` from #SHOPS data and refuse service outside the window.
RATIONALE: Maintains ROM trading schedules (e.g., Midgaard captain opens 6-22).
EXAMPLE: pytest -q tests/test_shops.py::test_shop_respects_open_hours
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
- Tick order: regen -> weather -> timers -> resets (match ROM cadence).
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
