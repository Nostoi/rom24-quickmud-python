# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.6.14] - 2026-04-28

Closes the `db2.c` audit (P1): all CRITICAL/IMPORTANT mob-loader gaps fixed.
Both `.are` and JSON loaders now match ROM `src/db2.c:load_mobiles` for AC
scaling, `ACT_IS_NPC` enforcement, race-table flag merge, and first-char
uppercase of long_descr/description. Two MINOR gaps (`DB2-004` kill_table,
`DB2-005` single-line fread_string) remain deferred — both documented as
not user-reachable in the current port.

### Fixed

- `DB2-003` — both mob loaders now uppercase the first character of
  `long_descr` and `description` at load time, mirroring ROM
  `src/db2.c:236-237` (`pMobIndex->long_descr[0] = UPPER(...)`).
  Previously mob protos with a lowercase first letter rendered that way in
  room/look output. `.are` loader normalizes after `read_string_tilde`;
  JSON loader normalizes inline at MobIndex construction.
- `DB2-006` — mob armor-class fields (`ac_pierce`/`ac_bash`/`ac_slash`/`ac_exotic`)
  are now multiplied by 10 at load time in both the `.are` loader
  (`mud/loaders/mob_loader.py`) and the JSON loader (`mud/loaders/json_loader.py`),
  mirroring ROM `src/db2.c:273-276`. Previously every loaded NPC had an AC value
  10× off in ROM's negative-AC convention, making them noticeably easier to hit.
  `mud/scripts/convert_are_to_json.py` now divides back when re-emitting JSON so
  the JSON files stay a faithful mirror of the raw `.are` upstream.
- `DB2-002` — both mob loaders now merge ROM `race_table[race].{act, aff,
  off, imm, res, vuln, form, parts}` flag bits into each loaded mob's
  letter-based flag fields, mirroring ROM `src/db2.c:239-242,279-286,295-297`.
  Previously race-derived intrinsics (dragon flying, troll regeneration,
  modron immunities, undead form/parts) were silently dropped at load time.
  Implemented in `mud/loaders/mob_loader.py:merge_race_flags`; the JSON
  loader (`mud/loaders/json_loader.py`) invokes it after MobIndex construction.
- `DB2-001` — both mob loaders now unconditionally OR `ACT_IS_NPC` (letter `A`)
  into every prototype's `act_flags` letter string, mirroring ROM
  `src/db2.c:239`. Previously a mob whose area-file flags omitted the `A`
  letter would spawn with `IS_NPC()` returning false, breaking every
  downstream `is_npc` check (combat, save, look, mobprog dispatch).

## [2.6.13] - 2026-04-28

Closes the cross-file dependency that blocked `interp.c` completion:
`WEAR-010` (do_wear dispatches weapons to wield) and `WEAR-011`
(do_hold auto-replaces) cleared the way for `INTERP-013` to collapse
`do_wield`/`do_hold` into aliases on `do_wear`, mirroring ROM
`cmd_table[]`. `interp.c` now closes at **24/24 fixed + 1
closed-deferred**.

### Fixed

- `act_obj.c:WEAR-010` — `do_wear` now dispatches `ITEM_WEAPON` items
  to the WIELD branch (`_dispatch_wield`) instead of rejecting with
  "You need to wield weapons, not wear them." Mirrors ROM
  `src/act_obj.c:1401-1697` `wear_obj` single-dispatcher design where
  `do_wear`/`do_wield`/`do_hold` are all the same function. Tests:
  `tests/integration/test_equipment_system.py::test_wear_010_do_wear_dispatches_weapon_to_wield`.
- `act_obj.c:WEAR-011` — `do_hold` now auto-unequips an existing held
  item via `_unequip_to_inventory()` instead of rejecting with
  "You're already holding {name}." Mirrors ROM
  `src/act_obj.c:1670-1677` `remove_obj(WEAR_HOLD, fReplace=TRUE)`
  semantics. Tests:
  `tests/integration/test_equipment_system.py::test_wear_011_do_hold_auto_replaces_existing_held`.
- `interp.c:INTERP-013` — `wield` and `hold` now dispatch to `do_wear`
  via the dispatcher's `aliases=("wield", "hold")` on the `wear`
  Command, mirroring ROM `cmd_table[]` (src/interp.c:103, 215, 232).
  `do_wield`/`do_hold` collapsed to thin wrappers around `do_wear`
  for direct-import callers. Closes `interp.c` to **24/24 fixed +
  1 closed-deferred** (100% of closeable gaps). Tests:
  `tests/integration/test_interp_dispatcher.py::test_interp_013_wear_wield_hold_share_do_wear`.

### Changed

- `wield <non-weapon>` and `hold <non-holdable>` no longer reject with
  command-specific errors ("You can't wield that." / "You can't hold
  that."). They now run the full `do_wear` dispatcher, so
  e.g. `wield ring` wears the ring on a finger — ROM-faithful since
  ROM has no separate `do_wield`/`do_hold` functions.
- `wield` and `hold` with no argument now emit
  `"Wear, wield, or hold what?"` instead of `"Wield what?"` /
  `"Hold what?"`, mirroring ROM's single-prompt design.

## [2.6.12] - 2026-04-28

Closes the remaining `interp.c` parser/extension gaps:
`INTERP-015` (port ROM `one_argument` to replace `shlex.split`) and
`INTERP-016` (verify `tail_chain` is a no-op in stock ROM and close-defer).
`interp.c` is now 22/24 gaps fixed + 1 closed-deferred + 1 deferred-pending
(`INTERP-013`, blocked on `ACT_OBJ_C` `do_wear` port).

### Fixed

- `interp.c:INTERP-015` — `_split_command_and_args` no longer routes
  through `shlex.split`; the new `_one_argument()` mirrors ROM
  `src/interp.c:766-798` byte-for-byte (lowercases head, single-char
  `'` and `"` quote sentinels with no nesting, backslash treated
  literally, surrounding whitespace stripped). `shlex` import dropped.
  Tests:
  `tests/integration/test_interp_dispatcher.py::test_interp_015_one_argument_matches_rom`
  (8 cases).

### Changed

- `interp.c:INTERP-016` — closed-deferred. Confirmed `tail_chain()`
  is `return;` only in stock ROM 2.4b6 (`src/db.c:3929`); empty
  hook used by some ROM derivatives for stack-tail-call extension.
  Stock-ROM behavior is "do nothing", which Python already matches
  by omission.
- `tests/test_alias_parity.py::test_alias_case_sensitivity` renamed
  to `test_alias_case_insensitive_lookup_matches_rom` and flipped to
  assert ROM-correct behavior — ROM `do_alias` stores keys via
  `one_argument` which lowercases (`src/alias.c:127, 217`), so an
  uppercase input head expands a lowercased alias key. The previous
  Python assertion mirrored pre-port `shlex` behavior, not ROM.

## [2.6.11] - 2026-04-28

Closes the three small position/trust gates left in `interp.c`
(`INTERP-004`/`-005`/`-006`). `interp.c` is now 20/24 gaps closed
(83%); only `INTERP-013` (deferred until `do_wear` ports the missing
wield/hold logic), `INTERP-015` (shlex/one_argument port), and
`INTERP-016` (`tail_chain` documentation, no-op) remain.

### Fixed

- `interp.c:INTERP-004` — `shout` now requires trust 3 to match ROM
  (`src/interp.c:200`). Previously had no `min_trust` (defaulted to 0).
  Test: `tests/integration/test_interp_dispatcher.py::test_interp_004_shout_requires_trust_3`.
- `interp.c:INTERP-005` — `murder` now requires trust 5 to match ROM
  (`src/interp.c:247`). Test:
  `test_interp_005_murder_requires_trust_5`.
- `interp.c:INTERP-006` — `music` `min_position` lowered from
  `RESTING` to `SLEEPING` to match ROM (`src/interp.c:93`). Test:
  `test_interp_006_music_min_position_sleeping`.

## [2.6.10] - 2026-04-27

Closes five more `interp.c` gaps: command-mapping cleanup
(`INTERP-009/010/011/012/014` — `hit`/`take`/`junk`/`tap`/`go`/`:`
now route to canonical handlers), `do_commands` column-padding fix
(`INTERP-024`), and the prefix-order sweep (`INTERP-017`) — Python's
prefix scan now mirrors ROM `cmd_table[]` declaration order via a
250-entry table, so 1- and 2-letter abbreviations resolve identically
to ROM. `INTERP-013` (collapse `do_wield`/`do_hold` into `do_wear`)
deferred — Python `do_wear` is missing strength/skill/two-hand checks
and HOLD auto-unequip that the separate functions currently provide;
collapsing now would regress behavior. `interp.c` is now 17/24 gaps
closed (71%).

### Fixed

- `interp.c:INTERP-009` — `"hit"` now dispatches to `do_kill` as a
  ROM-style alias on the kill `Command`; deleted redundant `do_hit`
  stub from `player_info.py` (`src/interp.c:88`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_009_hit_routes_to_do_kill`.
- `interp.c:INTERP-010` — `"take"` now dispatches to `do_get` as an
  alias on the get `Command`; deleted `do_take` stub
  (`src/interp.c:226`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_010_take_routes_to_do_get`.
- `interp.c:INTERP-011` — `"junk"` and `"tap"` now dispatch to
  `do_sacrifice` as aliases; deleted both stubs from `remaining_rom.py`
  (`src/interp.c:228-229`). Test:
  `test_interp_011_junk_tap_route_to_do_sacrifice`.
- `interp.c:INTERP-012` — `"go"` now dispatches to `do_enter` as an
  alias; deleted `do_go` stub (`src/interp.c:263`). Test:
  `test_interp_012_go_routes_to_do_enter`.
- `interp.c:INTERP-014` — `":"` now dispatches to `do_immtalk` as an
  alias; deleted `do_colon` stub from `typo_guards.py` whose
  `"Say what on the immortal channel?"` placeholder was masking ROM's
  NOWIZ toggle behavior (`src/interp.c:356`). Test:
  `test_interp_014_colon_routes_to_do_immtalk`.
- `interp.c:INTERP-024` — `do_commands`/`do_wizhelp` no longer strip
  trailing whitespace from rows; ROM emits each name as `%-12s` with
  full column padding preserved (`src/interp.c:815-823`). Test:
  `test_interp_024_do_commands_preserves_12char_column_padding`.
- `interp.c:INTERP-017` — `resolve_command` now walks a 250-entry
  ROM-faithful `_PREFIX_TABLE` in `src/interp.c` declaration order
  instead of Python's feature-grouped `COMMANDS` list; removed the
  exact-match shortcut so prefix resolution mirrors ROM
  `interpret()` exactly (e.g. `"go"` now resolves to `goto` not
  `enter`, matching ROM's hand-ordered prefix block). Sweep test:
  `tests/integration/test_interp_prefix_order.py::test_interp_017_prefix_winner_matches_rom`
  parses `src/interp.c` at collection time and asserts every
  single-letter prefix plus 20 curated 2-letter prefixes resolve
  identically to ROM (45 cases).

## [2.6.9] - 2026-04-27

Closes four `interp.c` dispatcher-level gaps in one session: empty-input
behavior (`INTERP-007`), ROM punctuation aliases (`INTERP-008`), snoop
forwarding (`INTERP-002`), and verified the wiznet `WIZ_SECURE` mirror
that was already in place (`INTERP-003`). `interp.c` is now 11/24 gaps
closed (46%).

### Fixed

- `interp.c:INTERP-007` — empty input now returns silently to match
  ROM `interpret()` (`src/interp.c:401-404`). Previously emitted the
  literal `"What?"`. Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_007_empty_input_returns_silently`.
- `interp.c:INTERP-008` — added ROM punctuation aliases `.` → `gossip`,
  `,` → `emote`, `/` → `recall` to `COMMAND_INDEX`
  (`src/interp.c:184,186,272`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_008_punctuation_aliases_route_to_rom_handlers`.
- `interp.c:INTERP-002` — `process_command` now forwards the input
  logline to `desc.snoop_by.character.messages` prefixed with `"% "`
  (`src/interp.c:491-496`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_002_snoop_forwards_logline_to_snooper`.
- `interp.c:INTERP-003` — verified `log_admin_command` already mirrors
  logged commands to wiznet `WIZ_SECURE` with ROM-style `$`/`{`
  doubling (`mud/admin_logging/admin.py:107-114`,
  `src/interp.c:468-489`). Audit row description was stale. Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_003_logged_command_mirrors_to_wiznet_secure`.

## [2.6.8] - 2026-04-27

Closes the immortal command trust drift (`INTERP-001`). All 43 commands
that were gated too low now match ROM `cmd_table[]` tier-for-tier. This
is a security-relevant fix — previously a `LEVEL_IMMORTAL` (52) character
could invoke commands ROM gates at L1..ML (53..60).

### Fixed

- `interp.c:INTERP-001` — raised `min_trust` on 43 immortal commands
  in `mud/commands/dispatcher.py` to match ROM `cmd_table[]` trust
  tiers (`src/interp.c:63-381`, `src/interp.h:34-44`). Affected
  tiers: ML, L1, L2, L3, L4, L5, L6, L7. Security-relevant — closes
  privilege drift where `LEVEL_IMMORTAL` (52) characters could
  invoke commands ROM gates at L1..ML (53..60). Test:
  `tests/integration/test_interp_trust.py::test_interp_001_command_trust_matches_rom` (50 parameters).

## [2.6.7] - 2026-04-27

`interp.c` social-cluster audit complete (6/6 social gaps closed). Both
remaining gaps (prefix lookup + literal "not found" message) shipped
with integration coverage; socials suite now 31/31. `interp.c` overall
audit progress: 6/24 gaps closed (25%) — non-social gaps (trust drift,
dispatcher hooks, command-mapping cleanup) remain open.

### Fixed

- `interp.c:INTERP-021` — social command lookup now mirrors ROM
  `str_prefix` semantics so partial names (e.g. `gigg` → `giggle`)
  resolve in load order. Added `mud.models.social.find_social()` and
  routed both the dispatcher fallback (`mud/commands/dispatcher.py`)
  and `perform_social` (`mud/commands/socials.py`) through it. Mirrors
  ROM `src/interp.c:584-592`.
- `interp.c:INTERP-022` — `perform_social` now emits the literal
  `"They aren't here."` when the targeted victim is absent, matching
  ROM `src/interp.c:637-640`. The fabricated `social.not_found` field
  (which has no counterpart in ROM's social table) is no longer used.

## [2.6.6] - 2026-04-27

`interp.c` ROM parity audit started — full audit doc with 24 stable gap
IDs (`INTERP-001`..`INTERP-024`) created. Closed the entire CRITICAL+
IMPORTANT social-cluster subset of `check_social` (`src/interp.c:597-685`):
position gates, NOEMOTE, sleeping snore exception, and the NPC slap/echo
auto-react via `mud.utils.rng_mm.number_bits(4)`. Socials integration
suite grew from 13 to 27 tests, all green.

### Fixed

- `interp.c:INTERP-018` — `perform_social` now refuses socials from
  characters in `Position.DEAD`, `MORTAL`, `INCAP`, or `STUNNED` and
  emits ROM's exact response messages
  (`"Lie still; you are DEAD."`, `"You are hurt far too bad for that."`,
  `"You are too stunned to do that."`). Mirrors
  `src/interp.c:603-616` (`check_social` position gate).
- `interp.c:INTERP-019` — sleeping characters now receive
  `"In your dreams, or what?"` for every social except `snore`
  (the canonical Furey exception). Mirrors `src/interp.c:618-626`.
- `interp.c:INTERP-020` — players punished with the `COMM_NOEMOTE`
  flag now receive `"You are anti-social!"` when attempting any
  social. NPCs are unaffected per ROM's `IS_NPC` short-circuit.
  Mirrors `src/interp.c:597-601`.

### Added

- `interp.c:INTERP-023` — NPC auto-reaction to player socials. When
  a non-NPC socials at an awake, non-charmed, non-switched NPC,
  `mud.utils.rng_mm.number_bits(4)` (0..15) decides the response:
  values 0..8 echo the social back at the player with the actor and
  victim swapped; values 9..12 produce a slap
  (`"$n slaps $N." / "You slap $N." / "$n slaps you."`); values 13..15
  fall through silently. Mirrors `src/interp.c:652-685`.

## [2.6.5] - 2026-04-27

`mob_prog.c` ROM parity audit complete — all 7 gaps closed (2 CRITICAL,
4 IMPORTANT, 1 MINOR). MOBprog predicate evaluation, greet/grall trigger
exclusivity, $-code expansion, and program-flow state-machine now match
ROM 2.4b6 behaviour.

### Fixed

- MOBPROG-007: `_program_flow` now logs a warning and aborts the program when
  an `if`/`or`/`and` keyword is not in ROM's `fn_keyword[]` table, mirroring
  the `bug()` + `return` paths at `src/mob_prog.c:1049-1056`, `1076-1083`,
  `1103-1109`. Typo'd predicates fail loudly instead of silently evaluating
  to False. Integration coverage at
  `tests/integration/test_mobprog_program_flow.py`. Also corrected the
  `test_simple_quest_accept_workflow` fixture program to use the real ROM
  keyword `carries` (not the previously-silent invalid `has_item`).
- MOBPROG-006: `_expand_arg` `$R` substitution now replicates the ROM
  long-standing bug at `src/mob_prog.c:798-799` — the visibility gate uses
  `rch` (random victim) but the substituted string is `ch->short_descr`
  (NPC actor) or `ch->name` (PC actor). Per AGENTS.md ROM Parity Rules,
  QuickMUD reproduces the bug. Integration coverage at
  `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-005: `_program_flow` `else` branch now resets
  `state[level] = IN_BLOCK` mirroring ROM `src/mob_prog.c:1138`. Structural
  state-machine parity only — no observable divergence on valid programs;
  regression coverage added at
  `tests/integration/test_mobprog_program_flow.py`.
- MOBPROG-004: `_cmd_eval` `clan` / `race` / `class` checks now resolve their
  name keyword via a ROM-style prefix lookup over `CLAN_TABLE`, `RACE_TABLE`,
  and `CLASS_TABLE` (mirroring ROM `clan_lookup` / `race_lookup` /
  `class_lookup`, `src/mob_prog.c:601-609`) instead of comparing the int
  attribute to the literal name string. `if class $n mage`,
  `if race $n dragon`, `if clan $n thieves` now match ROM. Integration
  coverage at `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-003: `_cmd_eval` `vnum` check now compares against `lval=0` when the
  target is a PC instead of returning False. Mirrors ROM `src/mob_prog.c:631-642`
  — `lval` initialises to 0 and is only overwritten for NPCs, so
  `if vnum $n == 0` is True against PCs and `if vnum $n != 0` is False.
  Integration coverage at `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-002: `mp_greet_trigger` no longer falls through to GRALL after a
  failed GREET percent roll. Mirrors ROM `src/mob_prog.c:1340-1345` where the
  GREET / GRALL branches are exclusive — a mob that is awake, can see the
  entrant, and has a GREET trigger only attempts GREET; GRALL is reserved for
  the busy/blind path. Integration coverage at
  `tests/integration/test_mobprog_greet_trigger.py`.
- MOBPROG-001: `_cmd_eval` `objexists` now walks `mud.models.obj.object_registry`
  (mirroring ROM `get_obj_world`, `src/mob_prog.c:399`) instead of only the
  current room and same-room carriers. Mob programs that gate on
  `if objexists <vnum|name>` against globally-placed items now match ROM
  semantics. Integration coverage at
  `tests/integration/test_mobprog_predicates.py`.

## [2.6.4] - 2026-04-27

`mob_cmds.c` ROM parity audit complete — all 18 gaps closed (6 CRITICAL,
9 IMPORTANT, 3 MINOR). MOBprog script commands (`mob kill`, `assist`,
`oload`, `flee`, `cast`, `call`, `damage`, `junk`, `purge`, `transfer`)
now match ROM 2.4b6 behaviour for charm/master defence, position gates,
target-type dispatch, level bounds, NO_MOB respect, recursion, and
bug-log emission on script authoring errors.

### Fixed

- MOBCMD-017: `do_mptransfer` now mirrors ROM's recursive structure — a
  literal `mob transfer all <loc>` recursively dispatches
  `do_mptransfer(ch, "<pcname> <loc>")` once per PC in the room
  (`src/mob_cmds.c:791-806`) so each victim re-runs the full validation
  pipeline (private-room check, location resolution). Previously the
  Python implementation inlined the iteration with a direct
  `_transfer_character` call. NPCs are skipped exactly as in ROM line
  799. Integration coverage at `tests/integration/test_mob_cmds_transfer.py`.
- MOBCMD-018: verified `do_mpflee` already checks `ch.fighting` as the
  first guard, mirroring ROM `src/mob_cmds.c:1266-1267`. The audit row
  was stale and is now closed without a code change.
- MOBCMD-007: `do_mppurge` no longer accepts the literal `"all"` token
  as a synonym for the no-arg purge-everything form. ROM
  `src/mob_cmds.c:631-665` treats an empty argument as purge-all and has
  no `"all"` keyword — the token falls through to the name-resolution
  branch like any other word. Also added the missing
  `Mppurge - Bad argument` (ROM line 663) and `Mppurge - Purging a PC`
  (ROM line 671) bug logs via the new `_bug()` helper. The previously
  divergent unit test (`test_mppurge_all_cleans_room`) now uses the
  no-arg form. Integration coverage at
  `tests/integration/test_mob_cmds_purge.py`.
- MOBCMD-013: `do_mpdamage` now emits a ROM-style `bug()` warning via
  Python's `logging` module when the min or max argument is non-numeric,
  mirroring ROM `src/mob_cmds.c:1105-1107` + `1113-1115`. Previously the
  function silently returned, swallowing what is a script-authoring
  error. A new module-local `_bug()` helper in `mud/mob_cmds.py` mirrors
  ROM's `bug("Mp... - <reason> from vnum %d.", vnum)` pattern; expect
  this helper to be reused as further `mob_cmds` gaps are closed.
  Integration coverage at
  `tests/integration/test_mob_cmds_damage.py::TestMpDamageNonNumericArgsBugLog`.
- MOBCMD-009: `do_mpflee` now respects `ROOM_NO_MOB` on a candidate
  destination when the fleeing character is an NPC, mirroring ROM
  `src/mob_cmds.c:1277-1280`. Previously script-driven NPC flees would
  pour mobs into rooms flagged NO_MOB. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py::TestMpFleeNoMobRoomFlag`.
- MOBCMD-006: `do_mpoload` now validates the optional level argument
  against ROM's `level < 0 || level > get_trust(ch)` check
  (`src/mob_cmds.c:575-580`) and refuses to spawn the object when out of
  range. Previously the level was accepted unconditionally so a script
  could load objects above the mob's trust ceiling. Integration coverage
  at `tests/integration/test_mob_cmds_oload.py`.
- MOBCMD-004: `do_mpjunk` (MOBprog `junk` script command) now matches
  ROM's empty-needle behaviour: `mob junk all.` (trailing dot, no
  suffix) discards nothing because ROM `src/mob_cmds.c:436` defers to
  `is_name(&arg[4], ...)` which returns FALSE for an empty string.
  Python had been short-circuiting on `not suffix` and discarding every
  carried object. Bare `mob junk all` still clears inventory as before.
  Integration coverage at `tests/integration/test_mob_cmds_junk.py`.
- MOBCMD-002: `do_mpassist` now enforces ROM `src/mob_cmds.c:393`'s full
  guard set — `victim == ch`, `ch->fighting != NULL`, and
  `victim->fighting == NULL`. Previously only the third clause was
  checked, so a script mob already in a fight could be redirected onto a
  new target via `mob assist`, and a script mob could nonsensically
  assist itself. Integration coverage at
  `tests/integration/test_mob_cmds_assist.py`.
- MOBCMD-001: `do_mpkill` now refuses when the script mob is charmed
  (`AffectFlag.CHARM`) and the chosen victim is its master, mirroring ROM
  `src/mob_cmds.c:364-369`. Previously a charmed mob scripted to
  `mob kill <master>` would attack its own charmer. Integration coverage
  at `tests/integration/test_mob_cmds_kill.py::TestMpKillCharmedMasterGuard`.
- MOBCMD-015 + MOBCMD-016: `do_mpcall` (MOBprog `call` script command) now
  parses the optional obj1/obj2 tokens from `mob call <vnum> <victim>
  <obj1> <obj2>` and resolves them via `_find_obj_here` (the `get_obj_here`
  analog), forwarding both to `mobprog.call_prog`. ROM
  `src/mob_cmds.c:1217-1252` initialises obj1/obj2 to NULL and only sets
  them when the corresponding token resolves through `get_obj_here`; the
  Python implementation had been dropping both args entirely so called
  sub-programs could never receive object context. Integration coverage at
  `tests/integration/test_mob_cmds_call.py`.
- MOBCMD-011 + MOBCMD-012: `do_mpcast` (MOBprog `cast` script command) now
  resolves the JSON `target` string into a canonical `_TargetType` IntEnum
  mirroring ROM `TAR_*` (`src/magic.h`) and dispatches on the enum, matching
  ROM's switch in `src/mob_cmds.c:1043-1066`. The previously string-keyed
  branches were drift-prone; in particular the `TAR_OBJ_CHAR_DEF/OFF/INV`
  cases now require an object (no character fallback) and `TAR_CHAR_DEFENSIVE`
  defaults to `ch` when the lookup fails, matching ROM lines 1055 + 1060-1065.
  Integration coverage at `tests/integration/test_mob_cmds_cast.py`.
- MOBCMD-003: `do_mpkill` now gates on `ch.position == Position.FIGHTING`
  (matching ROM `src/mob_cmds.c:361`) instead of the looser
  `ch.fighting is not None` check, and short-circuits self-attacks via the
  missing `victim is ch` guard from the same ROM line. Integration coverage
  at `tests/integration/test_mob_cmds_kill.py`.
- MOBCMD-008: `do_mpflee` now performs 6 `rng_mm.number_door()` random-door
  attempts before giving up, mirroring ROM `src/mob_cmds.c:1272-1286`.
  Previously the function iterated the exits list in order, so the first
  valid exit always won — wrong distribution for ROM-faithful flee
  behavior. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py::TestMpFleeRandomDoor`.
- MOBCMD-010: `do_mpflee` (MOBprog `flee` script command) now routes through
  `mud.world.movement.move_character` instead of the silent `_move_to_room`
  helper, mirroring ROM `src/mob_cmds.c:1283`
  (`move_char(ch, door, FALSE)`). Leave/arrive broadcasts, mp_exit/entry
  triggers, and the rest of the canonical movement pipeline now fire on
  script-driven flees. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py`.
- MOBCMD-005: `do_mpoload` (MOBprog `oload` script command) now accepts the
  optional `level` argument from `mob oload <vnum> [level] [R|W]`, mirroring
  ROM `src/mob_cmds.c:538-614`. When omitted, level defaults to
  `get_trust(ch)`; the spawned object's `level` is set post-spawn to mirror
  ROM `create_object(pObjIndex, level)`. Previously the level token was parsed
  but discarded, so script-loaded objects always took the prototype's raw
  level. Integration coverage at `tests/integration/test_mob_cmds_oload.py`.
- MOBCMD-014: `do_mpdamage` (MOBprog `damage` script command) now routes
  through `mud.combat.engine.apply_damage` instead of raw-decrementing
  `victim.hit`. Mirrors ROM `src/mob_cmds.c:1132-1145`
  (`damage(victim, victim, amount, TYPE_UNDEFINED, DAM_NONE, FALSE)`) so
  the death pipeline, position updates, fight triggers, and corpse
  handling fire on script-driven damage. Integration coverage at
  `tests/integration/test_mob_cmds_damage.py`.

### Changed

- `docs/parity/ACT_OBJ_C_AUDIT.md` and `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  refreshed to reflect that ROM `src/act_obj.c` is at 100% parity. Apr 27, 2026
  formal sweep verified all 12 audited functions
  (`do_get`/`do_put`/`do_drop`/`do_give`/`do_remove`/`do_sacrifice`/`do_quaff`/
  `do_drink`/`do_eat`/`do_fill`/`do_pour`/`do_recite`/`do_brandish`/`do_zap`
  plus `do_wear`/`do_wield`/`do_hold` and `do_steal`) against current Python;
  the recent batch commits (`97c901e` do_drop parity batch, `517542b` close
  get/put/drop/give/wear/sacrifice/recite/brandish/zap/steal gaps) closed all
  outstanding gaps. 193 act_obj-area integration tests green. P1 audited count
  rises from 5/11 (81%) to 6/11 (86%). No code changes — documentation
  reconciliation only.

## [2.6.3] - 2026-04-27

### Added

- Three project-local skills under `.claude/skills/` encoding the ROM 2.4b6 →
  Python parity loop: `rom-parity-audit` (file-level 5-phase audit),
  `rom-gap-closer` (single-gap TDD close flow), `rom-session-handoff`
  (end-of-session SESSION_SUMMARY + SESSION_STATUS + CHANGELOG generation).
- `CLAUDE.md` "Porting workflow" section: decision-tree mapping of when to
  invoke each skill plus dependencies between them.

### Changed

- `README.md` Project Status / badges refreshed to current state: version
  `2.6.2`, tests `3508/3521 passing` (99.6%) with 11 skipped and 2 known
  pre-existing failures, integration suite `1000+`, ROM 2.4b parity badge
  scoped to "gameplay 100%" (truer given the long tail of P2/P3 files), and
  active focus called out as `act_obj.c` (~60%).
- `AGENTS.md` Repo Hygiene §2 now requires that any change to README's
  Project Status / badges / metrics be accompanied in the same commit by a
  refresh of AGENTS.md tracker pointers and `docs/sessions/SESSION_STATUS.md`,
  preventing drift between the three surfaces. Underlying numbers stay
  sourced from `docs/parity/*` trackers.

## [2.6.2] - 2026-04-27

### Fixed

- **act_enter portal regressions** uncovered by the act_enter.c audit
  (PR #123):
  - `_stand_charmed_follower` now forwards `do_stand`'s returned string
    into the follower's message stream, so charmed sleepers receive the
    "You wake and stand up." text exactly as ROM `act_move.c:1044`
    sends inside `do_stand`.
  - `_portal_fade_out` now explicitly removes the portal from
    `room.contents` and clears `portal.location`. `game_loop._extract_obj`
    keys off `obj.in_room` but `Object` uses `obj.location`, so portal
    detachment after charge expiry was a silent no-op. Behavior now
    matches ROM `extract_obj(portal)` at `act_enter.c:212`.
  - `test_enter_closed_portal_denied`: corrected expected message to
    `"You can't seem to find a way in."` per ROM `act_enter.c:94`. The
    prior `"The portal is closed."` was the door-blocked message from
    `act_move.c`, not the portal path.
  - `test_move_through_portal_blocked_while_fighting`: corrected to
    assert silent return per ROM `act_enter.c:70-71`
    (`if (ch->fighting != NULL) return;`); removed the non-ROM
    `"No way!  You are still fighting!"` string.
- **`test_giant_strength_refuses_to_stack`** (was
  `test_stat_modifiers_stack_from_same_spell`): test asserted +4 STR after
  recasting giant strength, but ROM `src/magic.c:3022-3030`
  `spell_giant_strength` early-returns with "You are already as strong as
  you can get!" when the target is already affected. The Python
  implementation correctly mirrors ROM; the test was wrong. Rewrote the
  test to assert ROM anti-stack behavior.
- **`test_scavenger_prefers_valuable_items`**: flaky because the
  Mitchell-Moore RNG state leaks across tests, and the scavenger only acts
  on a 1/64 roll per `mobile_update` tick. Seed `rng_mm.seed_mm` to a
  known value at start of test and bump the iteration cap from 2000 to
  5000 for deterministic passes.

## [2.6.1] - 2026-04-27

### Added

- **act_enter.c parity (100% ROM parity for portal/enter mechanics):**
  Close all 15 ENTER-001..016 gaps documented in
  `docs/parity/ACT_ENTER_C_AUDIT.md`. 25 new integration tests in
  `tests/integration/test_act_enter_gaps.py`.

### Fixed

- **ENTER-009 (CRITICAL):** `do_enter` TO_CHAR message ("You enter $p." /
  "...somewhere else...") was being returned as a Python string and
  silently dropped — now delivered to the player.
- **ENTER-005:** Portal lookup uses `get_obj_list` (visibility,
  numbered syntax `2.portal`, keyword-list semantics) instead of fuzzy
  substring matching.
- **ENTER-004:** Non-portal objects and closed portals both produce
  `"You can't seem to find a way in."` (was diverging).
- **ENTER-008/010:** Departure/arrival TO_ROOM messages go through
  `act_format` + `broadcast_room` for correct `$n` invisibility
  resolution.
- **ENTER-011:** Portal fade-out only broadcasts in the old room when
  caller is in the old room; calls `extract_obj` on charge expiry.
- **ENTER-013:** `_get_random_room` capped at 100k iterations
  (was potentially returning None; ROM loops indefinitely).
- **ENTER-006/007/012:** Follower cascade — charmed followers stand
  before following, follower-name interpolation via `act_format`.
- **ENTER-002/003/014/015/016:** Cosmetic message wording matched to
  ROM and fighting-character silent-skip path.

## [2.6.0] - 2026-04-27

### Added

- **act_obj.c parity batch (100% ROM parity for object-manipulation
  commands):** do_get/do_put/do_drop/do_give/do_wear/do_remove/do_sacrifice/
  do_quaff/do_eat/do_drink/do_fill/do_pour/do_envenom/do_recite/do_brandish/
  do_zap/do_steal and shop commands (do_buy/do_sell/do_list/do_value).
  Adds full ROM TO_ROOM/TO_VICT/TO_NOTVICT broadcasts via act_format +
  broadcast_room. ~80 new integration tests under tests/integration/.
- **act_move.c parity batch:** do_stand/do_rest/do_sit/do_sleep/do_wake
  rewritten with full ROM furniture support (STAND/SIT/REST/SLEEP_AT/ON/IN
  with capacity checks and ch.on tracking). MOVE-001 arrival broadcast,
  MOVE-002 follower-name interpolation, SNEAK-001/HIDE-001 dispatcher
  delegation to canonical handlers. 40 new integration tests in
  tests/integration/test_position_commands.py.
- **act_comm.c P2 batch:** do_emote NOEMOTE check, do_pmote (~312 lines),
  do_colour, do_split gold+silver simultaneous-split fix, do_pose pose_table
  by class+level. New mud/utils/poses.py.
- **act_info.c P2 batch:** do_title/do_description/auto-settings family
  (autolist, autoassist, autoexit, autogold, autoloot, autopeek, autosac,
  autosplit, autotitle).
- LIQUID_TABLE in mud/models/constants.py extended with proof/full/thirst/
  food/ssize fields sourced from ROM src/const.c:886-931.
- WebSocket stream support (mud/network/websocket_stream.py) for the
  browser frontend; tests in tests/test_websocket_server.py.

### Changed

- **AGENTS.md rewritten:** ~700 lines → 275. Removed running session
  narrative, duplicated status reporting, stale "next steps". Added Session
  Notes (docs/sessions/) and Repo Hygiene (CHANGELOG / README / semver in
  pyproject.toml) sections modeled on quickmud-web-client/AGENTS.md.
- 79 SESSION_SUMMARY_*.md and HANDOFF_*.md files moved from repo root to
  `docs/sessions/`.

### Fixed

- `_obj_from_char()` now operates on `char.inventory` (was reading the
  wrong field, so transferred objects were not removed from giver).
- `count_users()` in mud/handler.py now reads `room.people` (room.characters
  does not exist).
- String-keyed equipment lookups replaced with `WearLocation` IntEnum keys
  across BRANDISH/ZAP/POUR families.
- Hardcoded hex flag values replaced with enum members
  (`PlayerFlag.AUTOSPLIT`, `WearFlag.NO_SAC`, `ItemType.STAFF/WAND`, etc).
- `do_steal` MAX_LEVEL set to 60 (was 51); STEAL-001..014 covering
  one_argument semantics, is_safe, is_clan, sleeping-victim wake, PC→PC
  PlayerFlag.THIEF, multi_hit signature, NODROP/INVENTORY checks,
  can_see_object visibility filter.
- `do_recite/do_brandish/do_zap` success paths were unrunnable due to
  undefined SkillTarget, bad ItemType references, string-keyed HOLD
  lookup; all 17 RECITE/BRANDISH/ZAP gaps closed.

## [2.5.2] - 2025-12-30

### Added

- **Command Integration ROM Parity Tests** (70 new tests):
  - `tests/test_act_comm_rom_parity.py` - 23 tests for communication commands (ROM `act_comm.c`)
    - Channel status display (`do_channels`)
    - Communication flag toggles (`do_deaf`, `do_quiet`, `do_afk`)
    - Channel blocking logic (QUIET, NOCHANNELS flags)
    - Delete command NPC blocking
    - Replay command behaviors
  - `tests/test_act_enter_rom_parity.py` - 22 tests for portal mechanics (ROM `act_enter.c`)
    - Random room selection with flag exclusions (`get_random_room`)
    - Portal entry mechanics (closed, curse, trust checks)
    - Portal charge system and flag handling (RANDOM, BUGGY, GOWITH)
    - Follower cascading through portals
  - `tests/test_act_wiz_rom_parity.py` - 25 tests for wiznet/admin commands (ROM `act_wiz.c`)
    - Wiznet channel toggle and flag management
    - Wiznet broadcast filtering (WIZ_ON, flag filters, min_level)
    - Admin commands (freeze, transfer, goto, trust)
    - Trust level enforcement

- **Documentation**:
  - `COMMAND_INTEGRATION_PARITY_REPORT.md` - Comprehensive command integration test completion report
    - Detailed ROM C to Python mapping for all 70 tests
    - Test philosophy and design decisions
    - ROM C source analysis summary
    - Quality metrics and coverage matrix

### Changed

- **ROM 2.4b6 Parity Certification Updates**:
  - Updated total ROM parity test count: 735 → 805 tests (+70)
  - Updated total test count: 2507 → 2577 tests (+70)
  - Added Command Integration Tests section to certification document
  - Updated ROM C source verification to include `act_comm.c`, `act_enter.c`, `act_wiz.c`

- **Test Coverage**:
  - Increased command integration test coverage (communication, portal, wiznet modules)
  - Total ROM parity tests: 805 (127 P0/P1/P2 + 608 combat/spells/skills + 70 command integration)

## [2.5.1] - 2025-12-30

### Added

- **Session Summary Documentation**:
  - `P0_P1_P2_EXTENDED_TESTING_SESSION_SUMMARY.md` - Verification session summary documenting that all P0/P1/P2 ROM C parity tests were already complete from previous sessions (December 29-30, 2025)

### Changed

- Updated README badges and project status to reflect complete ROM C parity test coverage (735 total ROM parity tests including 127 P0/P1/P2 formula verification tests)

## [2.5.0] - 2025-12-29

### Added

- **🎉 ROM 2.4b6 Parity Certification**: Official 100% ROM 2.4b6 behavioral parity certification
  - Created `ROM_2.4B6_PARITY_CERTIFICATION.md` - Comprehensive official certification document
  - 10 detailed subsystem parity matrices with ROM C source verification
  - Complete audit trail with 7 comprehensive audit documents (2000+ lines)
  - Integration test verification (43/43 passing = 100%)
  - Unit test coverage breakdown (700+ tests)
  - Differential testing methodology documented
  - Production readiness assessment
  - All 7 certification criteria verified and passing

- **Combat System Parity Verification** (100% Complete):
  - `COMBAT_PARITY_AUDIT_2025-12-28.md` - Comprehensive combat system audit
  - Added combat assist system (`mud/combat/assist.py`) with all ROM mechanics
  - Added 30+ combat tests (damage types, position multipliers, surrender command)
  - Verified all 32 ROM C combat functions implemented
  - Verified all 15 ROM combat commands functional
  - Position-based damage multipliers (sleeping 2x, resting/sitting 1.5x)
  - Damage resistance/vulnerability system complete
  - Special weapon effects (sharpness, vorpal, flaming, frost, vampiric, poison)

- **World Reset System Parity Verification** (100% Complete):
  - `WORLD_RESET_PARITY_AUDIT.md` - Comprehensive reset system audit
  - Verified all 7 ROM reset commands (M, O, P, G, E, D, R)
  - 49/49 reset tests passing with complete behavioral verification
  - Door state synchronization (bidirectional + one-way doors)
  - Exit randomization (Fisher-Yates shuffle)
  - ROM scheduling formula verified exact
  - Special cases documented (shop inventory, pet shops, infrared)

- **OLC Builders System Parity Verification** (100% Complete):
  - `OLC_PARITY_AUDIT.md` - Comprehensive OLC system audit
  - Verified all 5 ROM editors (@redit, @aedit, @oedit, @medit, @hedit)
  - 189/189 OLC tests passing with complete workflow verification
  - All 5 @asave variants functional
  - All 5 builder stat commands operational
  - Builder security system complete (trust levels, vnum ranges)

- **Security System Parity Verification** (100% Complete):
  - `SECURITY_PARITY_AUDIT.md` - Comprehensive security system audit
  - `SECURITY_PARITY_COMPLETION_SUMMARY.md` - Security session summary
  - Verified all 6 ROM ban flags (BAN_SUFFIX, PREFIX, NEWBIES, ALL, PERMIT, PERMANENT)
  - All 4 pattern matching modes (exact, prefix*, *suffix, *substring*)
  - 25/25 ban tests passing
  - Trust level enforcement verified
  - ROM file format compatibility verified

- **Object System Parity Verification** (100% Complete):
  - `OBJECT_PARITY_COMPLETION_REPORT.md` - Object system completion report
  - `docs/parity/OBJECT_PARITY_TRACKER.md` - Detailed 11-subsystem breakdown
  - Verified all 17 ROM object commands functional
  - 152/152 object tests passing + 277+ total object-related tests
  - Complete equipment system (11/11 wear mechanics)
  - Full container system (9/9 mechanics)
  - Exact encumbrance system (7/7 ROM C functions)
  - Complete shop economy (11/11 features)

- **Session Documentation**:
  - `SESSION_SUMMARY_2025-12-28.md` - Complete session documentation
  - `SESSION_SUMMARY_2025-12-27.md` - Previous session documentation

- **Additional Audit Documents**:
  - `SPELL_AFFECT_PARITY_AUDIT_2025-12-28.md` - Spell affect system verification
  - `COMBAT_GAP_VERIFICATION_FINAL.md` - Combat gap analysis and closure
  - `COMBAT_DAMAGE_RESISTANCE_COMPLETION.md` - Damage type system completion
  - `REMAINING_PARITY_GAPS_2025-12-28.md` - Final gap analysis (none remaining)
  - `COMMAND_AUDIT_2025-12-27_FINAL.md` - Command parity final verification

### Changed

- **README.md Updates**:
  - Updated version badge to 2.5.0
  - Updated ROM parity badge to link to official certification
  - Added "CERTIFIED" designation to ROM parity claim
  - Updated test counts to reflect integration test results (43/43 passing)
  - Added integration tests badge
  - Reorganized documentation section with certification first
  - Updated project status section with certification details

- **Documentation Organization**:
  - Added official certification as primary documentation
  - Reorganized docs to highlight certification achievement
  - Updated all parity references to point to certification

- **Test Organization**:
  - Added `tests/test_combat_assist.py` - Combat assist mechanics (14 tests)
  - Added `tests/test_combat_damage_types.py` - Damage resistance/vulnerability (15 tests)
  - Added `tests/test_combat_position_damage.py` - Position damage multipliers (10 tests)
  - Added `tests/test_combat_surrender.py` - Surrender command (5 tests)

### Fixed

- Combat damage vulnerability check now runs after immunity check (ROM parity fix)
- Corrected misleading "decapitation" comment on vorpal flag (ROM 2.4b6 has no decapitation)
- Updated outdated parity assessments in ROM_PARITY_FEATURE_TRACKER.md

### Verified

- ✅ **100% ROM 2.4b6 command coverage** (255/255 commands implemented)
- ✅ **100% integration test pass rate** (43/43 tests passing)
- ✅ **96.1% ROM C function coverage** (716/745 functions mapped)
- ✅ **All 10 major subsystems** verified with comprehensive audits
- ✅ **Production readiness** confirmed for players, builders, admins, developers

### Documentation

- 7 comprehensive audit documents totaling 2000+ lines
- Official ROM 2.4b6 parity certification document
- Complete ROM C source verification methodology
- Differential testing documentation
- Production deployment guidelines

## [2.4.0] - 2025-12-27

### Added

- **GitHub Release Creator Skill**: Comprehensive Claude Desktop skill for automated release management
  - Added `.claude/skills/github-release-creator/` with complete release automation tooling
  - Python script for automated release creation (`create_release.py`)
  - Shell scripts for release validation and creation
  - Changelog extraction utilities
  - Complete documentation with usage examples and workflows
  - GitHub CLI integration for professional release management
  - Support for semantic versioning, draft releases, and pre-releases

## [2.3.1] - 2025-12-27

### Added

- **Comprehensive Test Planning Documentation**:
  - Created `docs/validation/MOB_PARITY_TEST_PLAN.md` - Complete testing strategy for ROM 2.4b mob behaviors
    - 22 spec_fun behaviors (guards, dragons, casters, thieves)
    - 30+ ACT flag behaviors (aggressive, wimpy, scavenger, sentinel)
    - Damage modifiers (immunities, resistances, vulnerabilities)
    - Mob memory and tracking systems
    - Group assist mechanics
    - Wandering/movement AI
  - Created `docs/validation/PLAYER_PARITY_TEST_PLAN.md` - Complete testing strategy for player-specific behaviors
    - Information display commands (score, worth, whois)
    - Auto-settings (autoassist, autoloot, autogold, autosac, autosplit)
    - Conditions system (hunger, thirst, drunk, full)
    - Player flags and reputation (KILLER, THIEF)
    - Prompt customization
    - Title/description management
    - Trust/security levels
    - Player visibility states (AFK, wizinvis, incognito)
- **Claude Desktop Skill Support**:
  - Added `SKILL.md` - Comprehensive skill documentation for AI assistants
  - Added `.claude/skills/skill-creator/` - Anthropic's skill-creator tool
    - Skill validation scripts
    - Skill packaging utilities
    - Best practices documentation

### Changed

- **Test Organization**: Created clear roadmap for implementing 180+ behavioral tests
  - 6 major mob test areas (P0-P3 priority matrix)
  - 8 major player test areas (P0-P3 priority matrix)
  - 4-phase implementation roadmap for each
  - Complete test templates with ROM C references

### Documentation

- Documented 100+ specific test cases with ROM C source references
- Added implementation effort estimates and player impact assessments
- Created comprehensive testing guides for future development

## [2.3.0] - 2025-12-26

### Added

- **MobProg 100% ROM C Parity Achievement**: All 4 critical trigger hookups complete
  - `mp_give_trigger` integrated in do_give command
  - `mp_hprct_trigger` integrated in combat damage system
  - `mp_death_trigger` integrated in character death handling
  - `mp_speech_trigger` already integrated (verified)
- MobProg movement command validation in area file validator
- Comprehensive MobProg testing documentation (5 guides)
- Enhanced `validate_mobprogs.py` with movement command validation
- Organized validation and parity documentation structure

### Changed

- **Documentation Reorganization**: Created proper folder structure
  - Moved 10 documentation files to `docs/validation/` and `docs/parity/`
  - Moved 10 scripts to `scripts/validation/` and `scripts/parity/`
  - Moved 5 report files to appropriate `reports/` subfolders
  - Created 6 README files documenting folder contents
- Updated all cross-references in documentation to use new paths
- Enhanced validation scripts with movement command checks

### Fixed

- Integration test issues with Object creation and trigger signatures
- Syntax error in validate_mobprogs.py output formatting

## [2.2.1] - Previous Release

### Added

- Complete weapon special attacks system with ROM 2.4 parity (WEAPON_VAMPIRIC, WEAPON_POISON, WEAPON_FLAMING, WEAPON_FROST, WEAPON_SHOCKING)

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.3.0] - 2025-09-15

### Added

- Complete fighting state management with ROM 2.4 parity
- Character immortality protection following IS_IMMORTAL macro
- Level constants (MAX_LEVEL, LEVEL_IMMORTAL) matching ROM source

### Changed

### Deprecated

### Removed

### Fixed

- Character position initialization defaults to STANDING instead of DEAD
- Fighting state damage application and position updates
- Immortal character survival logic in combat system
- Combat defense order to match ROM 2.4 C source (shield_block → parry → dodge)

### Security

## [1.2.0] - 2025-09-15

### Added

- Complete telnet server with multi-user support
- Working shop system with buy/sell/list commands
- 132 skill system with handler stubs
- JSON-based world loading with 352 resets in Midgaard
- Admin commands (teleport, spawn, ban management)
- Communication system (say, tell, shout, socials)
- OLC building system for room editing
- pytest-timeout plugin for proper test timeouts

### Changed

- Achieved 100% test success rate (200/200 tests)
- Full test suite completes in ~16 seconds
- Modern async/await telnet server architecture
- SQLAlchemy ORM with migrations
- Comprehensive test coverage across all subsystems
- Memory efficient JSON area loading
- Optimized command processing pipeline
- Robust error handling throughout

### Fixed

- Character position initialization (STANDING vs DEAD)
- Hanging telnet tests resolved
- Enhanced error handling and null room safety
- Character creation now allows immediate command execution

## [0.1.1] - 2025-09-14

### Added

- Initial ROM 2.4 Python port foundation
- Basic world loading and character system
- Core command framework
- Database integration with SQLAlchemy

### Changed

- Migrated from legacy C codebase to pure Python
- JSON world data format for easier editing
- Modern Python packaging structure

## [0.1.0] - 2025-09-13

### Added

- Initial project structure
- Basic MUD framework
- ROM compatibility layer
- Core game loop implementation

[Unreleased]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.1...v1.2.0
[0.1.1]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Nostoi/rom24-quickmud-python/releases/tag/v0.1.0
